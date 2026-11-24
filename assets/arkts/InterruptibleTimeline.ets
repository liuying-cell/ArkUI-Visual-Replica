import { AnimatorResult } from '@kit.ArkUI';
import { hilog } from '@kit.PerformanceAnalysisKit';

const FULL_DURATION_MS = 1400;
const LOG_TAG = 'MotionTimeline';

interface TrackPhase {
  start: number;
  end: number;
  color: string;
}

const TRACKS: TrackPhase[] = [
  { start: 0, end: 0.62, color: '#D7FF57' },
  { start: 0.17, end: 0.78, color: '#B7A2FF' },
  { start: 0.34, end: 1, color: '#FFB18C' }
];

function smoothstep(value: number): number {
  const p = Math.max(0, Math.min(1, value));
  return p * p * (3 - 2 * p);
}

@Component
export struct InterruptibleTimeline {
  @State private progress: number = 0;
  @State private status: string = 'START';
  @State private reduced: boolean = false;
  private goal: number = 0;
  private runId: number = 0;
  private animator?: AnimatorResult;

  private cancelRun(): void {
    // Invalidate callbacks before cancel, including any synchronous callback.
    this.runId++;
    this.animator?.cancel();
    this.animator = undefined;
  }

  aboutToDisappear(): void {
    this.cancelRun();
  }

  private settle(goal: number): void {
    this.progress = goal;
    this.status = goal === 1 ? 'END' : 'START';
    hilog.info(0x0000, LOG_TAG, 'settle run=%{public}d progress=%{public}s', this.runId, goal.toFixed(4));
  }

  private toggle(): void {
    const from = this.progress;
    const goal = 1 - this.goal;
    this.goal = goal;
    this.cancelRun();
    const run = this.runId;
    const duration = Math.round(FULL_DURATION_MS * Math.abs(goal - from));
    hilog.info(0x0000, LOG_TAG, 'start run=%{public}d from=%{public}s goal=%{public}d ms=%{public}d',
      run, from.toFixed(4), goal, duration);
    if (this.reduced || duration < 1) {
      this.settle(goal);
      return;
    }
    this.status = goal === 1 ? 'FORWARD' : 'REVERSE';
    const animator = this.getUIContext().createAnimator({
      duration, easing: 'linear', delay: 0, fill: 'both', direction: 'normal', iterations: 1, begin: 0, end: 1
    });
    let firstFrame = true;
    animator.onFrame = (phase: number): void => {
      if (this.runId !== run) {
        return;
      }
      this.progress = from + (goal - from) * Math.max(0, Math.min(1, phase));
      if (firstFrame) {
        firstFrame = false;
        hilog.info(0x0000, LOG_TAG, 'first run=%{public}d progress=%{public}s', run, this.progress.toFixed(4));
      }
    };
    animator.onFinish = (): void => {
      if (this.runId === run) {
        this.animator = undefined;
        this.settle(goal);
      }
    };
    this.animator = animator;
    animator.play();
  }

  private toggleReduced(): void {
    this.reduced = !this.reduced;
    if (this.reduced) {
      this.cancelRun();
      this.settle(this.goal);
    }
  }

  private arrival(phase: TrackPhase): number {
    return smoothstep((this.progress - phase.start) / ((phase.end - phase.start) * 0.8));
  }

  private overshootSettle(phase: TrackPhase): number {
    const local = (this.progress - phase.start) / (phase.end - phase.start);
    return smoothstep((local - 0.8) / 0.2);
  }

  private markerScale(phase: TrackPhase): number {
    return 0.76 + 0.29 * this.arrival(phase) - 0.05 * this.overshootSettle(phase);
  }

  @Builder
  phaseTrack(phase: TrackPhase) {
    Stack({ alignContent: Alignment.Center }) {
      Row()
        .width(54)
        .height(14)
        .borderRadius(7)
        .backgroundColor(phase.color)
        .translate({ x: -66 + 140 * this.arrival(phase) - 8 * this.overshootSettle(phase) })
        .scale({ x: this.markerScale(phase), y: this.markerScale(phase) })
        .opacity(0.42 + 0.58 * this.arrival(phase))
    }
    .width('100%')
    .height(32)
    .borderRadius(16)
    .backgroundColor('#24292D')
    .accessibilityLevel('no-hide-descendants')
  }

  build() {
    Column() {
      Text('Interruptible timeline')
        .fontSize(22)
        .fontWeight(FontWeight.Bold)
        .fontColor('#F4F2E9')
        .margin({ bottom: 16 })
      Column({ space: 8 }) {
        this.phaseTrack(TRACKS[0])
        this.phaseTrack(TRACKS[1])
        this.phaseTrack(TRACKS[2])
      }
      .width('100%')
      .padding(12)
      .borderRadius(16)
      .backgroundColor('#14181B')
      .id('timeline-tracks')
      Row({ space: 8 }) {
        Button('Play / Reverse')
          .id('timeline-play')
          .height(44)
          .layoutWeight(1)
          .fontSize(12)
          .fontWeight(FontWeight.Bold)
          .backgroundColor('#D7FF57')
          .fontColor('#081004')
          .onClick(() => this.toggle())
        Button('Reduce motion')
          .id('timeline-reduce')
          .height(44)
          .layoutWeight(1)
          .fontSize(12)
          .backgroundColor(this.reduced ? '#B7A2FF' : '#262B30')
          .fontColor(this.reduced ? '#081004' : '#F4F2E9')
          .accessibilityDescription(this.reduced ? 'On' : 'Off')
          .onClick(() => this.toggleReduced())
      }
      .width('100%')
      .margin({ top: 16, bottom: 12 })
      Text(this.status)
        .id('timeline-status')
        .fontSize(12)
        .fontColor('#AEB4B5')
    }
    .alignItems(HorizontalAlign.Start)
    .width('100%')
    .constraintSize({ maxWidth: 400 })
    .padding(20)
  }
}
