import React from "react";
import ServiceQueuePage from "./ServiceQueuePage";

const ImagingPage = () => <ServiceQueuePage department="imaging" title="Imaging" endpoint="/imaging-queue" />;

export default ImagingPage;
