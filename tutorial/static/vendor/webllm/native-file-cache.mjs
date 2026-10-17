/* Native models already live in the verified Rust-managed disk store.
 * Never duplicate them in CacheStorage, IndexedDB, OPFS or the HTTP cache. */
export class NativeFileCache {
  check(url) {
    const u = new URL(url);
    if (!((u.protocol === 'asset:' && u.hostname === 'localhost') ||
          (u.protocol === 'http:' && u.hostname === 'asset.localhost'))) {
      throw new Error('Native model storage only accepts local asset URLs.');
    }
    return u.href;
  }
  async fetchWithCache(url, type, signal) {
    const response = await fetch(this.check(url), {cache: 'no-store', signal});
    if (!response.ok) throw new Error('Cannot read installed model: ' + response.status);
    if (type?.toLowerCase() === 'json') return response.json();
    if (type?.toLowerCase() === 'arraybuffer') return response.arrayBuffer();
    return response;
  }
  // Rust verifies every manifest file before this backend is constructed.
  async hasAllKeys(keys) { keys.forEach(url => this.check(url)); return true; }
  async addToCache(url) { this.check(url); }
  async deleteInCache(url) { this.check(url); } // Rust owns disk lifecycle.
}
