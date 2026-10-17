"""Keep the native disk backend when regenerating the vendored WebLLM bundle."""
from pathlib import Path
p=Path('tutorial/static/vendor/webllm/webllm.mjs')
s=p.read_text()
if "import {NativeFileCache}" not in s:
    for old,new in [
        ('if (normalized === "cache") {','if (normalized === "native-file") return "native-file";\n        if (normalized === "cache") {'),
        ('const cacheType = normalizeCacheType(options.cacheType);','const cacheType = normalizeCacheType(options.cacheType);\n        if (cacheType === "native-file") return new NativeFileCache();'),
    ]:
        if s.count(old)!=1: raise RuntimeError('WebLLM cache API changed; review native backend before rebuilding.')
        s=s.replace(old,new,1)
    p.write_text("import {NativeFileCache} from './native-file-cache.mjs';\n"+s)
