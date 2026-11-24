import { Want } from '@kit.AbilityKit';

/**
 * Small lifecycle-safe clock for autonomous visual effects.
 * The page owns the deterministic frame; this class only starts and stops ticking.
 */
export class MotionClock {
  private readonly intervalMs: number;
  private readonly onTick: () => void;
  private timerId: number = -1;

  constructor(intervalMs: number, onTick: () => void) {
    this.intervalMs = intervalMs;
    this.onTick = onTick;
  }

  start(frozen: boolean = false): void {
    this.stop();
    if (frozen) {
      return;
    }
    this.timerId = setInterval(() => {
      this.onTick();
    }, this.intervalMs);
  }

  setFrozen(frozen: boolean): void {
    this.start(frozen);
  }

  stop(): void {
    if (this.timerId !== -1) {
      clearInterval(this.timerId);
      this.timerId = -1;
    }
  }
}

/**
 * Call from UIAbility onCreate and onNewWant.
 * Supports both `--pb freezeMotion true` and a string-valued parameter.
 */
export function configureVisualTestFlags(want: Want): void {
  const rawFreeze: boolean | string | undefined =
    want.parameters?.['freezeMotion'] as boolean | string | undefined;
  AppStorage.setOrCreate<boolean>(
    'visualTestFreezeMotion',
    rawFreeze === true || rawFreeze === 'true'
  );
}

export function setVisualTestFreezeMotion(frozen: boolean): void {
  AppStorage.setOrCreate<boolean>('visualTestFreezeMotion', frozen);
}

export function visualMotionIsFrozen(): boolean {
  return AppStorage.get<boolean>('visualTestFreezeMotion') ?? false;
}
