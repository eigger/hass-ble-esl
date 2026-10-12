// Owns preview debounce, single-flight scheduling, and response freshness.
// The host supplies request and validity callbacks so this module stays free
// of editor, DOM, and Home Assistant details.
export class PreviewController {
  constructor({
    request,
    captureContext,
    isValid,
    onResult,
    onError,
    delay = 200,
  }) {
    this.request = request;
    this.captureContext = captureContext;
    this.isValid = isValid;
    this.onResult = onResult;
    this.onError = onError;
    this.delay = delay;
    this.sequence = 0;
    this.timer = null;
    this.inFlight = false;
    this.queued = false;
  }

  invalidate() {
    clearTimeout(this.timer);
    this.timer = null;
    this.sequence++;
    this.queued = false;
  }

  cancelScheduled() {
    clearTimeout(this.timer);
    this.timer = null;
  }

  schedule() {
    clearTimeout(this.timer);
    this.timer = null;
    const sequence = ++this.sequence;
    this.timer = setTimeout(() => {
      this.timer = null;
      if (this.inFlight) {
        this.queued = true;
        return;
      }
      void this.run(sequence);
    }, this.delay);
  }

  async run(sequence) {
    if (this.inFlight) {
      this.queued = true;
      return;
    }
    const context = this.captureContext();
    this.inFlight = true;
    try {
      const result = await this.request();
      if (this.isValid(context, sequence)) this.onResult(result);
    } catch (error) {
      if (this.isValid(context, sequence)) this.onError(error);
    } finally {
      this.inFlight = false;
      if (this.queued) {
        this.queued = false;
        this.schedule();
      }
    }
  }
}
