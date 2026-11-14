// Explicit build-only preload: no application/provider request may leave a build
// worker. The production bundle does not import this script.
globalThis.fetch=async()=>{throw new Error('Network disabled during isolated production build');};
