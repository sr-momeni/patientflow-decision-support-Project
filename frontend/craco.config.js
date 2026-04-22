const path = require('path');

module.exports = {
  webpack: {
    alias: {
      // Force all 'cookie' imports to resolve to the v0.6.0 compatible version
      'cookie': path.resolve(__dirname, 'node_modules/cookie/index.js'),
    },
  },
};
