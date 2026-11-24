export enum VisualLayoutClass {
  PHONE = 'phone',
  TABLET = 'tablet',
  WIDE = 'wide'
}

/**
 * One shared visual scale plus layout intents.
 * Do not use this to stretch a whole page to an unrelated aspect ratio.
 */
export class ResponsiveVisualScale {
  static readonly phoneMaxVp: number = 600;
  static readonly tabletMaxVp: number = 900;
  static readonly defaultMaxContentWidthVp: number = 520;
  static readonly defaultSideGutterVp: number = 24;
  static readonly defaultMinScale: number = 0.72;
  static readonly defaultMaxScale: number = 1.30;

  static layoutClass(viewportWidthVp: number): VisualLayoutClass {
    if (viewportWidthVp <= ResponsiveVisualScale.phoneMaxVp) {
      return VisualLayoutClass.PHONE;
    }
    if (viewportWidthVp <= ResponsiveVisualScale.tabletMaxVp) {
      return VisualLayoutClass.TABLET;
    }
    return VisualLayoutClass.WIDE;
  }

  static contentWidth(
    viewportWidthVp: number,
    maxContentWidthVp: number = ResponsiveVisualScale.defaultMaxContentWidthVp,
    sideGutterVp: number = ResponsiveVisualScale.defaultSideGutterVp
  ): number {
    if (viewportWidthVp <= ResponsiveVisualScale.phoneMaxVp) {
      return viewportWidthVp;
    }
    return Math.min(maxContentWidthVp, Math.max(0, viewportWidthVp - sideGutterVp * 2));
  }

  static scaleForContentWidth(
    contentWidthVp: number,
    designWidthVp: number,
    minScale: number = ResponsiveVisualScale.defaultMinScale,
    maxScale: number = ResponsiveVisualScale.defaultMaxScale
  ): number {
    if (designWidthVp <= 0) {
      return 1;
    }
    const rawScale: number = contentWidthVp / designWidthVp;
    return Math.min(maxScale, Math.max(minScale, rawScale));
  }

  static scaleForViewport(
    viewportWidthVp: number,
    designWidthVp: number,
    maxContentWidthVp: number = ResponsiveVisualScale.defaultMaxContentWidthVp
  ): number {
    const contentWidthVp: number =
      ResponsiveVisualScale.contentWidth(viewportWidthVp, maxContentWidthVp);
    return ResponsiveVisualScale.scaleForContentWidth(contentWidthVp, designWidthVp);
  }

  static vp(designPixels: number, scale: number): number {
    return designPixels * scale;
  }
}
