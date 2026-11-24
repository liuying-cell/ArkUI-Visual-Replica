import { curves } from '@kit.ArkUI';

interface FeedItem {
  tag: string;
  title: string;
  copy: string;
  accent: boolean;
}

interface TabItem {
  kicker: string;
  title: string;
  copy: string;
  background: string;
  accent: string;
}

@Entry
@Component
struct Index {
  @State selectedScene: number = 0;
  @State scrollProgress: number = 0;
  @State selectedTab: number = 0;
  @State segmentWidth: number = 100;
  @State buttonScale: number = 1;
  @State particleProgress: number = 0;
  @State particleOpacity: number = 0;
  @State reactionCount: number = 128;
  @State motionEnabled: boolean = true;
  @State ringScales: number[] = [1, 1, 1];
  @State ringOpacities: number[] = [0, 0, 0];

  private readonly particleX: number[] = [0, 51, 102.19, 86, 88.33, 59, 0, -51, -102.19, -86, -88.33, -59];
  private readonly particleY: number[] = [-86, -88.33, -59, 0, 51, 102.19, 86, 88.33, 59, 0, -51, -102.19];

  private swiperController: SwiperController = new SwiperController();
  private burstStartTimer: number = -1;
  private burstStopTimer: number = -1;

  private readonly feeds: FeedItem[] = [
    { tag: '01 / RHYTHM', title: 'Velocity becomes structure.', copy: 'Position feeds progress. Progress feeds hierarchy.', accent: false },
    { tag: '02 / PERCEPTION', title: 'The header remembers.', copy: 'A sticky surface keeps context while content moves beneath it.', accent: true },
    { tag: '03 / REST', title: 'Stop at a readable frame.', copy: 'The motion trace settles without overshooting the content.', accent: false }
  ];

  private readonly tabs: TabItem[] = [
    { kicker: '01 / PULSE', title: 'Short intervals, clear response.', copy: 'Tap a segment or drag the surface horizontally.', background: '#1E1930', accent: '#B7A2FF' },
    { kicker: '02 / DRIFT', title: 'Movement that keeps its place.', copy: 'The selected index owns the indicator and content.', background: '#132220', accent: '#8DE8E1' },
    { kicker: '03 / ORBIT', title: 'One system, three expressions.', copy: 'Release snaps to the nearest stable state.', background: '#241C17', accent: '#FFB18C' }
  ];

  aboutToDisappear(): void {
    if (this.burstStartTimer >= 0) {
      clearTimeout(this.burstStartTimer);
      this.burstStartTimer = -1;
    }
    if (this.burstStopTimer >= 0) {
      clearTimeout(this.burstStopTimer);
      this.burstStopTimer = -1;
    }
  }

  private selectScene(index: number): void {
    this.selectedScene = index;
  }

  private updateScrollProgress(offset: number): void {
    this.scrollProgress = Math.max(0, Math.min(1, this.scrollProgress + offset / 180));
  }

  private selectTab(index: number): void {
    this.selectedTab = index;
    this.swiperController.changeIndex(index, true);
  }

  private updateRing(index: number, scale: number, opacity: number): void {
    const scales = this.ringScales.slice();
    const opacities = this.ringOpacities.slice();
    scales[index] = scale;
    opacities[index] = opacity;
    this.ringScales = scales;
    this.ringOpacities = opacities;
  }

  private animateBurstRing(index: number, delay: number): void {
    this.getUIContext().animateTo({
      duration: 720,
      delay: delay,
      curve: Curve.EaseOut
    }, () => {
      const scales = this.ringScales.slice();
      const opacities = this.ringOpacities.slice();
      scales[index] = 1.75;
      opacities[index] = 0;
      this.ringScales = scales;
      this.ringOpacities = opacities;
    });
  }

  private triggerBurst(): void {
    this.reactionCount += 1;
    if (!this.motionEnabled) {
      return;
    }

    if (this.burstStartTimer >= 0) {
      clearTimeout(this.burstStartTimer);
    }
    if (this.burstStopTimer >= 0) {
      clearTimeout(this.burstStopTimer);
    }

    this.particleProgress = 0;
    this.particleOpacity = 0.92;
    this.buttonScale = 1;
    this.getUIContext().keyframeAnimateTo({
      onFinish: () => {
        this.buttonScale = 1;
      }
    }, [
      {
        duration: 110,
        curve: Curve.EaseIn,
        event: () => {
          this.buttonScale = 0.82;
        }
      },
      {
        duration: 170,
        curve: Curve.EaseOut,
        event: () => {
          this.buttonScale = 1.12;
        }
      },
      {
        duration: 200,
        curve: Curve.EaseOut,
        event: () => {
          this.buttonScale = 1;
        }
      }
    ]);

    this.ringScales = [0.7, 0.7, 0.7];
    this.ringOpacities = [0.55, 0.55, 0.55];
    for (let index = 0; index < 3; index++) {
      this.animateBurstRing(index, index * 72);
    }

    this.burstStartTimer = setTimeout(() => {
      this.getUIContext().animateTo({
        duration: 650,
        curve: Curve.EaseOut
      }, () => {
        this.particleProgress = 1;
        this.particleOpacity = 0;
      });
      this.burstStartTimer = -1;
    }, 16);
    this.burstStopTimer = setTimeout(() => {
      this.particleProgress = 0;
      this.particleOpacity = 0;
      this.burstStopTimer = -1;
    }, 900);
  }
  @Builder
  SceneTab(index: number, label: string) {
    Button(label)
      .layoutWeight(1)
      .height(34)
      .padding({ left: 3, right: 3 })
      .fontSize(9)
      .fontWeight(this.selectedScene === index ? FontWeight.Bold : FontWeight.Normal)
      .fontColor(this.selectedScene === index ? '#081004' : '#8C9190')
      .backgroundColor(this.selectedScene === index ? '#D7FF57' : Color.Transparent)
      .borderRadius(99)
      .onClick(() => this.selectScene(index))
  }

  @Builder
  SceneKicker(text: string) {
    Text(text)
      .fontSize(8)
      .letterSpacing(1.35)
      .fontWeight(FontWeight.Bold)
      .fontColor('#FFB18C')
  }

  @Builder
  FeedCard(item: FeedItem) {
    Column({ space: 9 }) {
      Text(item.tag)
        .fontSize(8)
        .letterSpacing(1.3)
        .fontColor(item.accent ? 'rgba(10,17,5,0.55)' : '#8C9190')
      Text(item.title)
        .fontSize(23)
        .lineHeight(24)
        .fontWeight(FontWeight.Medium)
        .fontColor(item.accent ? '#0A1105' : '#F4F2E9')
      Text(item.copy)
        .fontSize(10)
        .lineHeight(15)
        .fontColor(item.accent ? 'rgba(10,17,5,0.62)' : '#8C9190')
    }
    .alignItems(HorizontalAlign.Start)
    .width('100%')
    .padding(20)
    .backgroundColor(item.accent ? '#D7FF57' : 'rgba(255,255,255,0.035)')
    .border({ width: 1, color: item.accent ? Color.Transparent : 'rgba(255,255,255,0.09)' })
    .borderRadius(20)
  }

  @Builder
  ScrollScene() {
    Stack({ alignContent: Alignment.TopStart }) {
      Row() {
        Text('FIELD NOTES').fontSize(8).letterSpacing(1.4).fontWeight(FontWeight.Bold).fontColor('#F4F2E9')
        Blank()
        Text('00 — 03').fontSize(8).letterSpacing(1.4).fontWeight(FontWeight.Bold).fontColor('#F4F2E9')
      }
      .width('100%')
      .height(46)
      .padding({ left: 20, right: 20 })
      .backgroundColor('rgba(9,12,14,0.88)')
      .border({ width: { bottom: 1 }, color: 'rgba(255,255,255,0.08)' })
      .zIndex(3)
      .opacity(this.scrollProgress)
      .translate({ y: -12 + this.scrollProgress * 12 })

      Row() {
        Row()
          .width('100%')
          .height(2)
          .backgroundColor('#D7FF57')
          .scale({ x: this.scrollProgress, y: 1 })
      }
      .width('100%')
      .height(2)
      .zIndex(4)

      List({ space: 12 }) {
        ListItem() {
          Column() {
            Text('02')
              .fontSize(170)
              .fontColor('rgba(255,255,255,0.025)')
              .fontFamily('serif')
              .position({ x: 190, y: -18 })
            this.SceneKicker('SCROLL / PROGRESS')
            Text() {
              Span('Signals\n')
              Span('in motion.').fontColor('#D7FF57').fontFamily('serif')
            }
            .fontSize(38)
            .lineHeight(36)
            .fontColor('#F4F2E9')
            .margin({ top: 9 })
            Text('Scroll the field. The masthead condenses while the hero recedes and a progress trace follows the gesture.')
              .fontSize(11)
              .lineHeight(17)
              .fontColor('#8C9190')
              .width(278)
              .margin({ top: 14 })
          }
          .alignItems(HorizontalAlign.Start)
          .width('100%')
          .height(296)
          .padding({ top: 56 })
          .clip(true)
          .translate({ y: -this.scrollProgress * 24 })
          .scale({ x: 1 - this.scrollProgress * 0.06, y: 1 - this.scrollProgress * 0.06 })
          .opacity(1 - this.scrollProgress * 0.72)
        }
        ForEach(this.feeds, (item: FeedItem) => {
          ListItem() {
            this.FeedCard(item)
          }
        }, (item: FeedItem) => item.tag)
      }
      .width('100%')
      .height('100%')
      .padding({ left: 22, right: 22, bottom: 28 })
      .edgeEffect(EdgeEffect.Spring)
      .onDidScroll((scrollOffset: number) => {
        this.updateScrollProgress(scrollOffset);
      })
    }
    .width('100%')
    .height('100%')
  }
  @Builder
  TabPanel(item: TabItem, index: number) {
    Stack({ alignContent: Alignment.TopStart }) {
      Row()
        .width(170)
        .height(170)
        .borderRadius(85)
        .border({ width: 1, color: item.accent })
        .backgroundColor('rgba(255,255,255,0.015)')
        .position({ x: 178, y: 18 })
      Row()
        .width(56)
        .height(56)
        .borderRadius(28)
        .backgroundColor(item.accent)
        .shadow({ radius: 20, color: item.accent, offsetY: 0 })
        .position({ x: 235, y: 75 })
      Column({ space: 9 }) {
        this.SceneKicker(item.kicker)
        Text(item.title)
          .fontSize(29)
          .lineHeight(29)
          .fontWeight(FontWeight.Medium)
          .fontColor('#F4F2E9')
          .width(240)
          .margin({ top: 64 })
        Text(item.copy)
          .fontSize(10)
          .lineHeight(15)
          .fontColor('rgba(255,255,255,0.54)')
      }
      .alignItems(HorizontalAlign.Start)
      .padding(24)
    }
    .width('100%')
    .height('100%')
    .clip(true)
    .backgroundColor(item.background)
    .id(`tab-panel-${index}`)
  }

  @Builder
  TabsScene() {
    Column() {
      this.SceneKicker('GESTURE / SWIPE')
      Text('Three signals.')
        .fontSize(32)
        .fontColor('#F4F2E9')
        .fontWeight(FontWeight.Medium)
        .margin({ top: 8 })
      Stack({ alignContent: Alignment.TopStart }) {
        Stack({ alignContent: Alignment.TopStart }) {
          Row()
            .width(this.segmentWidth)
            .height(30)
            .borderRadius(99)
            .backgroundColor('#B7A2FF')
            .translate({ x: this.selectedTab * this.segmentWidth })
            .animation({ duration: 440, curve: curves.springMotion(0.55, 0.85) })
          Row() {
            ForEach([0, 1, 2], (item: number) => {
              Button(['Pulse', 'Drift', 'Orbit'][item])
                .layoutWeight(1)
                .height(30)
                .fontSize(9)
                .fontColor(this.selectedTab === item ? '#100C1F' : '#8C9190')
                .fontWeight(this.selectedTab === item ? FontWeight.Bold : FontWeight.Normal)
                .backgroundColor(Color.Transparent)
                .onClick(() => this.selectTab(item))
            }, (item: number) => item.toString())
          }
          .width('100%')
          .height(30)
        }
        .width('100%')
        .height('100%')
        .onAreaChange((oldArea: Area, newArea: Area) => {
          const width = Number.parseFloat(newArea.width.toString());
          if (width > 0) {
            this.segmentWidth = width / 3;
          }
        })
      }
      .width('100%')
      .height(40)
      .padding(4)
      .backgroundColor('rgba(255,255,255,0.025)')
      .border({ width: 1, color: 'rgba(255,255,255,0.1)' })
      .borderRadius(99)
      .margin({ top: 18 })

      Swiper(this.swiperController) {
        ForEach(this.tabs, (item: TabItem, index: number) => {
          this.TabPanel(item, index)
        }, (item: TabItem) => item.kicker)
      }
      .width('100%')
      .height(252)
      .indicator(false)
      .loop(false)
      .duration(440)
      .curve(Curve.EaseOut)
      .onChange((index: number) => {
        this.selectedTab = index;
      })
      .borderRadius(22)
      .clip(true)

      Row() {
        Text(`INDEX 0${this.selectedTab}`).fontSize(8).letterSpacing(1.1).fontColor('rgba(255,255,255,0.34)')
        Blank()
        Text('DRAG OR TAP').fontSize(8).letterSpacing(1.1).fontColor('rgba(255,255,255,0.34)')
      }
      .width('100%')
      .padding({ left: 5, right: 5, top: 11 })
    }
    .alignItems(HorizontalAlign.Start)
    .width('100%')
    .height('100%')
    .padding({ left: 18, right: 18, top: 24 })
  }

  @Builder
  BurstParticleLayer() {
    Stack({ alignContent: Alignment.Center }) {
      ForEach([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], (index: number) => {
        Row()
          .width(7)
          .height(7)
          .borderRadius(2)
          .backgroundColor(['#D7FF57', '#B7A2FF', '#8DE8E1', '#FFB18C'][index % 4])
          .translate({
            x: this.particleX[index] * this.particleProgress,
            y: this.particleY[index] * this.particleProgress
          })
          .rotate({ angle: this.particleProgress * 90 })
          .opacity(this.particleOpacity)
      }, (index: number) => index.toString())
    }
    .width(300)
    .height(240)
    .hitTestBehavior(HitTestMode.None)
  }

  @Builder
  BurstScene() {
    Column() {
      Column({ space: 8 }) {
        this.SceneKicker('KEYFRAME / RETRIGGER')
        Text('Make it land.')
          .fontSize(32)
          .fontColor('#F4F2E9')
          .fontWeight(FontWeight.Medium)
      }
      .width('100%')

      Stack({ alignContent: Alignment.Center }) {
        ForEach([0, 1, 2], (item: number) => {
          Row()
            .width(116)
            .height(116)
            .borderRadius(36)
            .border({ width: 1, color: 'rgba(215,255,87,0.38)' })
            .scale({ x: this.ringScales[item], y: this.ringScales[item] })
            .opacity(this.ringOpacities[item])
        }, (item: number) => item.toString())
        if (this.motionEnabled) {
          this.BurstParticleLayer()
        }
        Button() {
          Text('✦').fontSize(44).fontColor('#101500')
        }
        .width(106)
        .height(106)
        .borderRadius(34)
        .backgroundColor('#D7FF57')
        .border({ width: 1, color: 'rgba(215,255,87,0.45)' })
        .shadow({ radius: 28, color: 'rgba(215,255,87,0.22)', offsetY: 10 })
        .scale({ x: this.buttonScale, y: this.buttonScale })
        .onClick(() => this.triggerBurst())
      }
      .width('100%')
      .height(240)

      Row() {
        Row({ space: 12 }) {
          Text('REACTIONS').fontSize(8).letterSpacing(1.3).fontColor('#8C9190')
          Text(this.reactionCount.toString()).fontSize(30).fontColor('#F4F2E9')
        }
        Blank()
        Button(this.motionEnabled ? 'MOTION ON' : 'MOTION OFF')
          .height(28)
          .padding({ left: 10, right: 10 })
          .fontSize(8)
          .fontColor(this.motionEnabled ? '#D7FF57' : '#8C9190')
          .backgroundColor(Color.Transparent)
          .border({ width: 1, color: this.motionEnabled ? 'rgba(215,255,87,0.24)' : 'rgba(255,255,255,0.1)' })
          .borderRadius(99)
          .onClick(() => {
            this.motionEnabled = !this.motionEnabled;
          })
      }
      .width('100%')
      .padding({ left: 4, right: 4, bottom: 11 })
      .border({ width: { bottom: 1 }, color: 'rgba(255,255,255,0.1)' })

      Text('Tap repeatedly. The keyframe sequence restarts from the settled button frame; rings and particles are cancelled before re-entry.')
        .fontSize(10)
        .lineHeight(15)
        .fontColor('#8C9190')
        .margin({ top: 11 })
    }
    .alignItems(HorizontalAlign.Start)
    .width('100%')
    .height('100%')
    .padding({ left: 20, right: 20, top: 24 })
  }
  build() {
    Column() {
      Row() {
        Row({ space: 8 }) {
          Row()
            .width(7)
            .height(7)
            .borderRadius(4)
            .backgroundColor('#D7FF57')
            .shadow({ radius: 10, color: '#D7FF57' })
          Text('MOTION LAB')
            .fontSize(10)
            .fontWeight(FontWeight.Bold)
            .letterSpacing(1.8)
            .fontColor('#F4F2E9')
        }
        Blank()
        Text('ARKUI / 02')
          .fontSize(9)
          .letterSpacing(1.6)
          .fontColor('#8C9190')
      }
      .width('100%')
      .height(24)

      Column() {
        Text('ADVANCED MOTION STUDY')
          .fontSize(8)
          .letterSpacing(1.5)
          .fontWeight(FontWeight.Bold)
          .fontColor('#D7FF57')
        Text() {
          Span('System\n')
          Span('motion.').fontColor('#B7A2FF').fontFamily('serif')
        }
        .fontSize(43)
        .lineHeight(38)
        .fontWeight(FontWeight.Medium)
        .fontColor('#F4F2E9')
        .margin({ top: 8 })
        Text('Scroll progress, direct horizontal manipulation, and retriggerable keyframe feedback.')
          .fontSize(10)
          .lineHeight(15)
          .fontColor('#8C9190')
          .width(315)
          .margin({ top: 10 })
      }
      .alignItems(HorizontalAlign.Start)
      .width('100%')
      .padding({ top: 23, bottom: 16 })

      Row({ space: 4 }) {
        this.SceneTab(0, '01 Scroll')
        this.SceneTab(1, '02 Tabs')
        this.SceneTab(2, '03 Burst')
      }
      .width('100%')
      .padding(4)
      .backgroundColor('rgba(255,255,255,0.025)')
      .border({ width: 1, color: 'rgba(255,255,255,0.1)' })
      .borderRadius(99)

      Stack({ alignContent: Alignment.TopStart }) {
        if (this.selectedScene === 0) {
          this.ScrollScene()
        } else if (this.selectedScene === 1) {
          this.TabsScene()
        } else {
          this.BurstScene()
        }
      }
      .width('100%')
      .height(430)
      .margin({ top: 11 })
      .clip(true)
      .backgroundColor('#0D1012')
      .border({ width: 1, color: 'rgba(255,255,255,0.1)' })
      .borderRadius(28)

      Row() {
        Text('●  390 × 844').fontSize(8).letterSpacing(1.1).fontColor('rgba(255,255,255,0.32)')
        Text('60 FPS TARGET').fontSize(8).letterSpacing(1.1).fontColor('rgba(255,255,255,0.32)')
        Text('T+01').fontSize(8).letterSpacing(1.1).fontColor('rgba(255,255,255,0.32)')
      }
      .justifyContent(FlexAlign.SpaceBetween)
      .width('100%')
      .height(38)
    }
    .width('100%')
    .height('100%')
    .padding({ left: 20, right: 20, top: 12, bottom: 8 })
    .backgroundColor('#090C0E')
  }
}