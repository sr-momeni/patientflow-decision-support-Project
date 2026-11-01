// Cookie shim — exports all functions compatible with ESM named imports
// This shim intercepts any `import { parse } from 'cookie'` requests
// and re-exports from the CommonJS-compatible cookie@0.6.0

var cookie = require('cookie');

// Named exports for ESM compatibility
exports.parse = cookie.parse;
exports.serialize = cookie.serialize;

// Default export
module.exports = cookie;
module.exports.parse = cookie.parse;
module.exports.serialize = cookie.serialize;
