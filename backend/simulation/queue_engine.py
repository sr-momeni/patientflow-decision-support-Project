"""Shared, deterministic finite-cohort resource simulation.

FCFS and strict CTAS use exactly the same nurse, physician, bed and diagnostic
resources. Predictive changes only bed holds. This is NOT an ED-to-inpatient
pathway model: ED/ICU are separate service pools with fixed patient routing.
"""
from collections import deque
from datetime import timedelta
import heapq
import itertools
import math
from .event_model import HospitalState
from backend.ml.predictor import HighUrgencyPredictor


class QueueEngine:
    def __init__(self, ed_capacity, icu_capacity, policy='FCFS', predictor=None,
                 reservation_threshold=.8, reservation_timeout_minutes=30,
                 scenario=None, observation_start=None, observation_end=None,
                 capture_snapshots=False, assessment_minutes=15):
        if ed_capacity <= 0 or icu_capacity < 0:
            raise ValueError('Invalid bed capacities')
        if policy not in ('FCFS', 'CTAS', 'Predictive'):
            raise ValueError('Unknown scheduling policy')
        if reservation_timeout_minutes <= 0 or assessment_minutes <= 0:
            raise ValueError('Durations must be positive')
        self.state = HospitalState(ed_capacity, icu_capacity)
        self.cap = {'ED': ed_capacity, 'ICU': icu_capacity}
        self.policy, self.predictor = policy, predictor
        if policy == 'Predictive' and predictor is None:
            raise ValueError('Predictive scheduling requires a predictor')
        self.threshold, self.timeout = reservation_threshold, reservation_timeout_minutes
        self.scenario = scenario
        self.start, self.end = observation_start, observation_end
        self.capture_snapshots = capture_snapshots
        self.assessment_minutes = assessment_minutes
        self.snapshots, self.reservation_log = [], []
        self.metrics = dict(total_reservations=0, successful_catches=0, expired_reservations=0,
                            cancelled_reservations=0, reservation_duration_minutes=0.,
                            reserved_idle_bed_minutes=0., blocked_idle_bed_minutes=0.)
        self._ran = False

    def run(self, patients):
        if self._ran:
            raise ValueError('Use a fresh engine for each run')
        self._ran = True
        if not patients:
            return
        if len({p.id for p in patients}) != len(patients):
            raise ValueError('Patient ids must be unique')
        self.start = self.start or min(p.arrival for p in patients)
        self.end = self.end or max(p.arrival for p in patients) + timedelta(microseconds=1)
        horizon = (self.end - self.start).total_seconds()/60
        if horizon <= 0:
            raise ValueError('Observation end must follow start')
        self.patients = patients
        self.seq = itertools.count()
        self.events = []
        self.free = self.cap.copy()
        self.active = {}
        self.past = deque()
        self.queues = {'ED': [], 'ICU': []}
        self.triage_q = []
        self.nurses = self.scenario.nurses if self.scenario else len(patients)
        self.doctors = self.scenario.physicians if self.scenario else len(patients)
        self.lab_free = self.imaging_free = 0.
        self.holds = {}
        self.peak = {'ED': 0, 'ICU': 0}
        self.horizon = horizon
        for i,p in enumerate(patients):
            if p.bed_type not in self.cap or self.cap[p.bed_type] == 0:
                raise ValueError('Patient requires a bed pool with zero capacity; no silent rerouting')
            if p.urgency not in range(1,6) or not math.isfinite(p.los_minutes) or p.los_minutes <= 0 or p.triage_minutes < 0:
                raise ValueError('Invalid patient acuity or duration')
            t = (p.arrival-self.start).total_seconds()/60
            if not 0 <= t < horizon:
                raise ValueError('Arrival outside declared observation window')
            self._push(t, 3, 'arrival', i)
        if self.capture_snapshots or self.policy == 'Predictive':
            tick = 0.
            while tick < horizon:
                self._push(tick, 2, 'tick', None)
                tick += 15
        self._push(horizon, 1, 'close', None)
        previous=0.
        while self.events:
            now=self.events[0][0]
            dt=now-previous
            for bed in self.holds:
                self.metrics['reservation_duration_minutes'] += dt
                if self.free[bed] > 0:
                    self.metrics['reserved_idle_bed_minutes'] += dt
                    if self.queues[bed] and self.doctors > 0 and self.free[bed] <= 1:
                        self.metrics['blocked_idle_bed_minutes'] += dt
            previous=now
            forecast=None
            expired_here=set()
            # Release all same-time events before admission; stable numeric tie order.
            while self.events and self.events[0][0] == now:
                _,_,_,kind,value=heapq.heappop(self.events)
                if kind=='arrival':
                    p=patients[value]
                    self.past.append((now,p.urgency))
                    heapq.heappush(self.triage_q,(p.arrival,value))
                elif kind=='triaged':
                    self.nurses+=1
                    p=patients[value]
                    p.triage_end=self._date(now)
                    heapq.heappush(self.queues[p.bed_type],self._key(value))
                elif kind=='doctor_free':
                    self.doctors+=1
                    self._diagnostics(value,now,'lab')
                elif kind=='lab_done':
                    self._diagnostics(value,now,'imaging')
                elif kind=='imaging_done':
                    self._diagnostics(value,now,'done')
                elif kind=='discharge':
                    p=patients[value]
                    del self.active[value]
                    self.free[p.bed_type]+=1
                elif kind=='expire':
                    bed,token=value
                    if bed in self.holds and self.holds[bed]['token']==token:
                        self._finish_hold(bed,now,'expired')
                        expired_here.add(bed)
                elif kind=='close':
                    for bed in list(self.holds):
                        self._finish_hold(bed,now,'cancelled_at_horizon')
                elif kind=='tick':
                    features=self._features(now)
                    snapshot={'time':self._date(now), 'features':features.tolist(),
                              'past_high_60m':sum(t >= now-60 and u<=2 for t,u in self.past)}
                    if self.capture_snapshots:
                        self.snapshots.append(snapshot)
                    if self.policy=='Predictive':
                        forecast=self.predictor.predict(self._date(now),features[4],features[5],
                            dict(zip(('15m','30m','1h','4h'),features[6:10])),
                            dict(zip((1,2,3),features[10:13])))
                # Triage is FCFS for all policies; CTAS is known at its completion.
                while self.nurses and self.triage_q:
                    _,idx=heapq.heappop(self.triage_q)
                    p=patients[idx]
                    p.triage_start=self._date(now)
                    self.nurses-=1
                    self._push(now+p.triage_minutes,4,'triaged',idx)
            if forecast is not None and forecast >= self.threshold and now < horizon:
                for bed in self.cap:
                    if self.free[bed] and bed not in self.holds and bed not in expired_here:
                        q=self.queues[bed]
                        # Do not credit a forecast for patients already waiting.
                        if q and patients[q[0][-1]].urgency<=2:
                            continue
                        token=next(self.seq)
                        self.holds[bed]={'token':token,'start':now}
                        self.metrics['total_reservations']+=1
                        self._push(min(now+self.timeout,horizon),1,'expire',(bed,token))
            self._admit(now)
        if any(self.queues.values()) or self.triage_q or self.active or self.holds:
            raise RuntimeError('Simulation did not drain all queues')
        assert all(p.discharge is not None for p in patients)
        assert self.metrics['total_reservations']==sum(self.metrics[x] for x in
            ('successful_catches','expired_reservations','cancelled_reservations'))

    def _date(self,t):
        return self.start+timedelta(minutes=t)

    def _push(self,t,order,kind,value):
        heapq.heappush(self.events,(t,order,next(self.seq),kind,value))

    def _key(self,idx):
        p=self.patients[idx]
        return (0 if self.policy=='FCFS' else p.urgency,p.arrival,idx)

    def _features(self,now):
        while self.past and self.past[0][0] < now-240:
            self.past.popleft()
        rates={key:sum(now-width<=t<now for t,_ in self.past)
               for key,width in [('15m',15),('30m',30),('1h',60),('4h',240)]}
        acuity={k:sum(p.urgency==k for p in self.active.values()) for k in (1,2,3)}
        return HighUrgencyPredictor()._extract_features(self._date(now),
            (self.cap['ED']-self.free['ED'])/self.cap['ED'],
            (self.cap['ICU']-self.free['ICU'])/max(1,self.cap['ICU']),rates,acuity)[0]

    def _finish_hold(self,bed,now,reason,patient=None):
        hold=self.holds.pop(bed)
        counter='successful_catches' if reason=='caught_future_high_urgency' else (
            'expired_reservations' if reason=='expired' else 'cancelled_reservations')
        self.metrics[counter]+=1
        self.reservation_log.append({'bed_type':bed,'start':self._date(hold['start']),
            'end':self._date(now),'duration_minutes':now-hold['start'],'reason':reason,
            'patient_id':patient.id if patient else None})

    def _admit(self,now):
        while self.doctors:
            candidates=[]
            for bed,q in self.queues.items():
                if not q or not self.free[bed]:
                    continue
                p=self.patients[q[0][-1]]
                if bed in self.holds and self.free[bed]<=1 and p.urgency>2:
                    continue
                candidates.append((q[0],bed))
            if not candidates:
                break
            _,bed=min(candidates)
            idx=heapq.heappop(self.queues[bed])[-1]
            p=self.patients[idx]
            if bed in self.holds and self.free[bed]<=1:
                hold=self.holds[bed]
                reason='caught_future_high_urgency' if p.arrival>=self._date(hold['start']) else 'cancelled_for_existing_patient'
                self._finish_hold(bed,now,reason,p)
            p.service_start=self._date(now)
            p.wait_minutes=(p.service_start-p.arrival).total_seconds()/60
            self.free[bed]-=1
            self.peak[bed]=max(self.peak[bed],self.cap[bed]-self.free[bed])
            self.doctors-=1
            doctor_end=now+self.assessment_minutes
            p.physician_end=self._date(doctor_end)
            self._push(doctor_end,0,'doctor_free',idx)
            self.active[idx]=p

    def _diagnostics(self,idx,now,stage):
        p=self.patients[idx]
        if stage=='lab' and self.scenario and p.lab_required:
            start=max(now,self.lab_free)
            end=start+60/self.scenario.lab_slots_per_hour
            self.lab_free=end
            p.lab_start,p.lab_end=self._date(start),self._date(end)
            self._push(end,0,'lab_done',idx)
            return
        if stage in ('lab','imaging') and self.scenario and p.imaging_required:
            start=max(now,self.imaging_free)
            end=start+60/self.scenario.imaging_slots_per_hour
            self.imaging_free=end
            p.imaging_start,p.imaging_end=self._date(start),self._date(end)
            self._push(end,0,'imaging_done',idx)
            return
        service_start=(p.service_start-self.start).total_seconds()/60
        done=max(now,service_start+p.los_minutes)
        p.discharge=self._date(done)
        self._push(done,0,'discharge',idx)
