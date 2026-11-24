import { curves } from '@kit.ArkUI';

interface MotionCard {
  code: string;
  tag: string;
  title: string;
  meter: number;
}

@Entry
@Component
struct Index {
  @State selectedScene: number = 0;
  @State stackRevealed: boolean = false;
  @State sheetOffset: number = 228;
  @State sheetExpanded: boolean = false;
  @State orbExpanded: boolean = false;
  @State geometryId: string = '';

  private readonly sheetClosedOffset: number = 228;
  private sheetGestureStart: number = 228;
  private readonly cards: MotionCard[] = [
    { code: 'A1', tag: 'RESPONSE', title: 'Fast lane', meter: 72 },
    { code: 'B2', tag: 'RHYTHM', title: 'Soft cascade', meter: 88 },
    { code: 'C3', tag: 'SETTLE', title: 'Quiet land', meter: 54 }
  ];

  aboutToAppear(): void {
    setTimeout(() => {
      this.stackRevealed = true;
    }, 80);
  }

  private selectScene(index: number): void {
    this.selectedScene = index;
    if (index === 0) {
      this.replayStack();
    }
  }

  private replayStack(): void {
    this.stackRevealed = false;
    setTimeout(() => {
      this.stackRevealed = true;
    }, 24);
  }

  private openSheet(): void {
    this.sheetExpanded = true;
    this.getUIContext().animateTo({
      curve: curves.springMotion(0.45, 0.82)
    }, () => {
      this.sheetOffset = 0;
    });
  }

  private closeSheet(): void {
    this.sheetExpanded = false;
    this.getUIContext().animateTo({
      curve: curves.springMotion(0.45, 0.82)
    }, () => {
      this.sheetOffset = this.sheetClosedOffset;
    });
  }

  private finishSheetDrag(velocityY: number): void {
    const threshold = this.sheetClosedOffset * 0.35;
    const shouldOpen = this.sheetOffset < threshold || velocityY < -300;
    this.sheetExpanded = shouldOpen;
    this.getUIContext().animateTo({
      curve: curves.springMotion(0.45, 0.8)
    }, () => {
      this.sheetOffset = shouldOpen ? 0 : this.sheetClosedOffset;
    });
  }

  private toggleOrb(): void {
    this.geometryId = 'meridian-orb';
    this.getUIContext().animateTo({
      duration: 520,
      curve: curves.cubicBezierCurve(0.2, 0.8, 0.2, 1),
      onFinish: () => {
        this.geometryId = '';
      }
    }, () => {
      this.orbExpanded = !this.orbExpanded;
    });
  }

  @Builder
  SceneTab(index: number, label: string) {
    Button(label)
      .layoutWeight(1)
      .height(34)
      .padding({ left: 4, right: 4 })
      .fontSize(9)
      .fontWeight(this.selectedScene === index ? FontWeight.Bold : FontWeight.Normal)
      .fontColor(this.selectedScene === index ? '#07100C' : '#8D93A1')
      .backgroundColor(this.selectedScene === index ? '#91F2D0' : Color.Transparent)
      .borderRadius(99)
      .onClick(() => this.selectScene(index))
  }

  @Builder
  StageLabel(index: string, label: string) {
    Row({ space: 6 }) {
      Text(index).fontSize(9).letterSpacing(1.3).fontColor('#FF9B7A')
      Text(label).fontSize(9).letterSpacing(1.3).fontColor('rgba(255,255,255,0.42)')
    }
    .position({ x: 18, y: 18 })
  }

  @Builder
  StackCard(item: MotionCard, index: number) {
    Row({ space: 12 }) {
      Text(item.code)
        .width(36)
        .height(36)
        .textAlign(TextAlign.Center)
        .fontSize(10)
        .fontWeight(FontWeight.Bold)
        .fontColor('#91F2D0')
        .backgroundColor('rgba(145,242,208,0.09)')
        .borderRadius(12)
      Column({ space: 4 }) {
        Text(item.tag)
          .fontSize(8)
          .letterSpacing(1.2)
          .fontColor('#8D93A1')
        Text(item.title)
          .fontSize(14)
          .fontColor('#F3F5F8')
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1)
      Stack({ alignContent: Alignment.Start }) {
        Row().width('100%').height(4).borderRadius(2).backgroundColor('rgba(255,255,255,0.1)')
        Row()
          .width(`${item.meter}%`)
          .height(4)
          .borderRadius(2)
          .linearGradient({ angle: 90, colors: [['#7DA8FF', 0], ['#91F2D0', 1]] })
      }
      .width(64)
      .height(4)
    }
    .width(306)
    .height(70)
    .padding({ left: 14, right: 14 })
    .margin({ left: index * 14, bottom: 7 })
    .backgroundColor('rgba(255,255,255,0.055)')
    .border({ width: 1, color: 'rgba(255,255,255,0.085)' })
    .borderRadius(18)
    .opacity(this.stackRevealed ? 1 : 0)
    .translate({ y: this.stackRevealed ? 0 : 34 })
    .scale({ x: this.stackRevealed ? 1 : 0.93, y: this.stackRevealed ? 1 : 0.93 })
    .animation({
      duration: 620,
      delay: index * 85,
      curve: curves.springMotion(0.55, 0.86)
    })
  }

  @Builder
  StackScene() {
    Stack({ alignContent: Alignment.TopStart }) {
      this.StageLabel('01', 'TIMELINE / STAGGER')
      Column() {
        ForEach(this.cards, (item: MotionCard, index: number) => {
          this.StackCard(item, index)
        }, (item: MotionCard) => item.code)
      }
      .position({ x: 22, y: 56 })
      Button() {
        Row({ space: 8 }) {
          Text('↻').fontSize(15)
          Text('Replay sequence').fontSize(10)
        }
      }
      .height(42)
      .padding({ left: 17, right: 17 })
      .fontColor('#91F2D0')
      .backgroundColor('rgba(145,242,208,0.075)')
      .border({ width: 1, color: 'rgba(145,242,208,0.24)' })
      .borderRadius(99)
      .position({ x: 104, y: 310 })
      .onClick(() => this.replayStack())
      Text('620 MS · 85 MS STAGGER · SPRING-LIKE SETTLE')
        .fontSize(8)
        .letterSpacing(1.1)
        .fontColor('rgba(255,255,255,0.3)')
        .width('100%')
        .textAlign(TextAlign.Center)
        .position({ x: 0, y: 360 })
    }
    .width('100%')
    .height('100%')
  }

  @Builder
  SheetScene() {
    Stack({ alignContent: Alignment.TopStart }) {
      this.StageLabel('02', 'GESTURE / SPRING')
      Column({ space: 5 }) {
        Text('NOW PLAYING').fontSize(9).letterSpacing(1.4).fontWeight(FontWeight.Bold).fontColor('#FF9B7A')
        Text('Quiet signal').fontSize(26).fontColor('#F3F5F8')
        Text('Harbor lights · 04:18').fontSize(11).fontColor('#8D93A1')
        Row({ space: 4 }) {
          ForEach([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], (item: number) => {
            Row()
              .width(3)
              .height(18 + (item % 4) * 9)
              .borderRadius(2)
              .linearGradient({ angle: 90, colors: [['#91F2D0', 0], ['#7DA8FF', 1]] })
          }, (item: number) => item.toString())
        }
        .height(52)
        .margin({ top: 12 })
      }
      .alignItems(HorizontalAlign.Start)
      .position({ x: 24, y: 70 })

      Text('TAP OR PULL UP')
        .fontSize(8)
        .letterSpacing(1.8)
        .fontColor('rgba(255,255,255,0.44)')
        .position({ x: 128, y: 286 })
        .onClick(() => this.openSheet())

      if (this.sheetOffset < 120) {
        Row()
          .width('100%')
          .height('100%')
          .backgroundColor('rgba(0,0,0,0.25)')
          .onClick(() => this.closeSheet())
      }

      Column() {
        Row()
          .width(42)
          .height(4)
          .borderRadius(2)
          .backgroundColor('rgba(255,255,255,0.25)')
          .margin({ top: 15, bottom: 14 })
        Row() {
          Column({ space: 2 }) {
            Text('PLAYBACK').fontSize(9).letterSpacing(1.4).fontWeight(FontWeight.Bold).fontColor('#FF9B7A')
            Text('Quiet signal').fontSize(26).fontColor('#F3F5F8')
          }
          .alignItems(HorizontalAlign.Start)
          .layoutWeight(1)
          Text(this.sheetOffset < 80 ? 'OPEN' : 'CLOSED')
            .fontSize(8)
            .letterSpacing(1)
            .fontColor('#8D93A1')
            .padding({ left: 8, right: 8, top: 5, bottom: 5 })
            .border({ width: 1, color: 'rgba(255,255,255,0.1)' })
            .borderRadius(99)
        }
        .width('100%')
        Stack({ alignContent: Alignment.Start }) {
          Row().width('100%').height(3).borderRadius(2).backgroundColor('rgba(255,255,255,0.11)')
          Row().width('30%').height(3).borderRadius(2).backgroundColor('#91F2D0')
        }
        .width('100%')
        .height(3)
        .margin({ top: 22 })
        Row() {
          Text('01:12').fontSize(8).letterSpacing(1.2).fontColor('rgba(255,255,255,0.36)')
          Blank()
          Text('04:18').fontSize(8).letterSpacing(1.2).fontColor('rgba(255,255,255,0.36)')
        }
        .width('100%')
        .margin({ top: 7 })
        Row() {
          Text('‹').fontSize(25).fontColor('rgba(255,255,255,0.6)')
          Text('▶')
            .width(52)
            .height(52)
            .textAlign(TextAlign.Center)
            .fontSize(16)
            .fontColor('#06110D')
            .backgroundColor('#91F2D0')
            .borderRadius(26)
            .margin({ left: 34, right: 34 })
          Text('›').fontSize(25).fontColor('rgba(255,255,255,0.6)')
        }
        .justifyContent(FlexAlign.Center)
        .width('100%')
        .margin({ top: 7 })
        Text('Drag the surface. Release above the threshold or with upward velocity; the sheet inherits motion instead of restarting.')
          .fontSize(10)
          .lineHeight(15)
          .fontColor('#8D93A1')
          .margin({ top: 7 })
      }
      .alignItems(HorizontalAlign.Start)
      .width('100%')
      .height(316)
      .padding({ left: 22, right: 22, bottom: 16 })
      .backgroundColor('#171B25')
      .border({ width: 1, color: 'rgba(255,255,255,0.11)' })
      .borderRadius({ topLeft: 28, topRight: 28 })
      .position({ x: 0, y: 74 })
      .translate({ y: this.sheetOffset })
      .gesture(
        PanGesture({ fingers: 1, direction: PanDirection.Vertical })
          .onActionStart(() => {
            this.sheetGestureStart = this.sheetOffset;
          })
          .onActionUpdate((event: GestureEvent) => {
            this.sheetOffset = Math.max(0, Math.min(this.sheetClosedOffset,
              this.sheetGestureStart + event.offsetY));
          })
          .onActionEnd((event: GestureEvent) => {
            this.finishSheetDrag(event.velocityY);
          })
      )
    }
    .width('100%')
    .height('100%')
  }

  @Builder
  OrbToken(size: number, radius: number) {
    Stack({ alignContent: Alignment.Center }) {
      Text('M')
        .fontSize(size * 0.42)
        .fontColor('rgba(6,17,13,0.72)')
        .fontFamily('serif')
    }
    .width(size)
    .height(size)
    .borderRadius(radius)
    .linearGradient({
      angle: 135,
      colors: [['#91F2D0', 0], ['#7DA8FF', 0.55], ['#FF9B7A', 1]]
    })
    .border({ width: 1, color: 'rgba(255,255,255,0.28)' })
    .shadow({ radius: 26, color: 'rgba(125,168,255,0.24)', offsetY: 12 })
    .geometryTransition(this.geometryId)
    .transition(TransitionEffect.OPACITY)
  }

  @Builder
  OrbHome() {
    Column() {
      this.OrbToken(62, 17)
      Text('FEATURED OBJECT')
        .fontSize(9)
        .letterSpacing(1.4)
        .fontWeight(FontWeight.Bold)
        .fontColor('#FF9B7A')
        .margin({ top: 46 })
      Text('Meridian orb')
        .fontSize(26)
        .fontColor('#F3F5F8')
        .margin({ top: 5 })
      Text('A shared element keeps identity while its frame, scale and corner radius change.')
        .fontSize(10)
        .lineHeight(15)
        .fontColor('#8D93A1')
        .width(250)
        .margin({ top: 7 })
      Button() {
        Row({ space: 20 }) {
          Text('Open object').fontSize(10)
          Text('↗').fontSize(14).fontColor('#91F2D0')
        }
      }
      .height(38)
      .padding({ left: 14, right: 14 })
      .fontColor('#F3F5F8')
      .backgroundColor('rgba(255,255,255,0.055)')
      .border({ width: 1, color: 'rgba(255,255,255,0.13)' })
      .borderRadius(12)
      .margin({ top: 10 })
      .onClick(() => this.toggleOrb())
    }
    .alignItems(HorizontalAlign.Start)
    .width('100%')
    .height('100%')
    .padding({ left: 26, right: 26, top: 100 })
    .id('orb-home')
  }

  @Builder
  OrbDetail() {
    Stack({ alignContent: Alignment.TopStart }) {
      Column() {
        this.OrbToken(116, 58)
        Text('OBJECT 07')
          .fontSize(9)
          .letterSpacing(1.4)
          .fontWeight(FontWeight.Bold)
          .fontColor('#FF9B7A')
          .margin({ top: 13 })
        Text('Meridian\norb')
          .fontSize(32)
          .lineHeight(30)
          .textAlign(TextAlign.Center)
          .fontColor('#F3F5F8')
          .margin({ top: 6 })
        Text('Geometry transition. One object becomes the destination surface without a fade-shaped handoff.')
          .fontSize(10)
          .lineHeight(15)
          .textAlign(TextAlign.Center)
          .fontColor('#8D93A1')
          .width(270)
          .margin({ top: 8 })
        Row() {
          Text('RADIUS 50%').fontSize(8).letterSpacing(1.1).fontColor('rgba(255,255,255,0.38)')
          Blank()
          Text('FRAME 1 → 1.8').fontSize(8).letterSpacing(1.1).fontColor('rgba(255,255,255,0.38)')
        }
        .width(290)
        .padding({ top: 10 })
        .border({ width: { top: 1 }, color: 'rgba(255,255,255,0.1)' })
      }
      .width('100%')
      .padding({ top: 56 })
      .alignItems(HorizontalAlign.Center)
      Button() {
        Text('×').fontSize(20).fontColor('#F3F5F8')
      }
      .width(34)
      .height(34)
      .backgroundColor('rgba(255,255,255,0.06)')
        .border({ width: 1, color: 'rgba(255,255,255,0.1)' })
        .borderRadius(17)
        .position({ x: 297, y: 17 })
        .onClick(() => this.toggleOrb())
    }
    .width('100%')
    .height('100%')
    .backgroundColor('rgba(255,155,122,0.045)')
    .id('orb-detail')
  }

  @Builder
  OrbScene() {
    Stack({ alignContent: Alignment.TopStart }) {
      this.StageLabel('03', 'GEOMETRY / SHARED')
      if (this.orbExpanded) {
        this.OrbDetail()
      } else {
        this.OrbHome()
      }
    }
    .width('100%')
    .height('100%')
  }

  build() {
    Column() {
      Row() {
        Row({ space: 9 }) {
          Row().width(7).height(7).borderRadius(4).backgroundColor('#91F2D0').shadow({ radius: 10, color: '#91F2D0' })
          Text('MOTION LAB').fontSize(10).fontWeight(FontWeight.Bold).letterSpacing(1.8).fontColor('#F3F5F8')
        }
        Blank()
        Text('ARKUI / 01').fontSize(9).letterSpacing(1.8).fontColor('#8D93A1')
      }
      .width('100%')
      .height(28)

      Column() {
        Text('NATIVE MOTION STUDY').fontSize(9).letterSpacing(1.6).fontWeight(FontWeight.Bold).fontColor('#91F2D0')
        Text() {
          Span('Motion\n')
          Span('grammar.').fontColor('#FF9B7A').fontFamily('serif')
        }
        .fontSize(55)
        .lineHeight(49)
        .fontWeight(FontWeight.Medium)
        .fontColor('#F3F5F8')
        .margin({ top: 8 })
        Text('Three interaction studies for temporal fidelity: choreography, gesture physics and shared geometry.')
          .fontSize(12)
          .lineHeight(18)
          .fontColor('#8D93A1')
          .width(290)
          .margin({ top: 16 })
      }
      .alignItems(HorizontalAlign.Start)
      .width('100%')
      .padding({ top: 24, bottom: 14 })

      Row({ space: 4 }) {
        this.SceneTab(0, '01 Timeline')
        this.SceneTab(1, '02 Sheet')
        this.SceneTab(2, '03 Shared')
      }
      .width('100%')
      .padding(4)
      .backgroundColor('rgba(255,255,255,0.03)')
      .border({ width: 1, color: 'rgba(255,255,255,0.1)' })
      .borderRadius(99)

      Stack({ alignContent: Alignment.TopStart }) {
        if (this.selectedScene === 0) {
          this.StackScene()
        } else if (this.selectedScene === 1) {
          this.SheetScene()
        } else {
          this.OrbScene()
        }
      }
      .width('100%')
      .height(390)
      .margin({ top: 12 })
      .clip(true)
      .backgroundColor('#0E1118')
      .border({ width: 1, color: 'rgba(255,255,255,0.1)' })
      .borderRadius(28)

      Row() {
        Text('●  390 × 844').fontSize(8).letterSpacing(1.2).fontColor('rgba(255,255,255,0.34)')
        Text('60 FPS TARGET').fontSize(8).letterSpacing(1.2).fontColor('rgba(255,255,255,0.34)')
        Text('T+01').fontSize(8).letterSpacing(1.2).fontColor('rgba(255,255,255,0.34)')
      }
      .justifyContent(FlexAlign.SpaceBetween)
      .width('100%')
      .height(46)
    }
    .width('100%')
    .height('100%')
    .padding({ left: 20, right: 20, top: 12, bottom: 8 })
    .backgroundColor('#090B10')
  }
}