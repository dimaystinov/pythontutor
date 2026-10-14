class TutorPCM extends AudioWorkletProcessor {
    constructor() { super(); this.sum=0;this.count=0;this.phase=0;this.samples=[]; }
    process(inputs) {
        const input=inputs[0] && inputs[0][0];
        if (!input) return true;
        const ratio=sampleRate/16000;
        for (const value of input) {
            this.sum+=value;this.count++;this.phase++;
            if (this.phase>=ratio) {
                this.samples.push(this.sum/this.count);this.phase-=ratio;this.sum=0;this.count=0;
                if(this.samples.length>=2048) { this.port.postMessage(Float32Array.from(this.samples));this.samples=[]; }
            }
        }
        return true;
    }
}
registerProcessor('tutor-pcm',TutorPCM);
