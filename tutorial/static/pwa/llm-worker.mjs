import {WebWorkerMLCEngineHandler} from '../vendor/webllm/webllm.mjs?v=github1';
const handler=new WebWorkerMLCEngineHandler();
self.onmessage=event=>handler.onmessage(event);
