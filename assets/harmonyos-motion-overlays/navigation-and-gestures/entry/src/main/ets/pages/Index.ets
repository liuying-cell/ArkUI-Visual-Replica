import { curves } from '@kit.ArkUI';

interface MotionRow {
  id: number;
  title: string;
  copy: string;
  hot: boolean;
}

interface StackItem {
  index: string;
  title: string;
}

@Entry
@Component
struct Index {
  @State selectedScene: number = 0;
  @State rows: MotionRow[] = [
    { id: 1, title: 'Signal captured', copy: 'BASELINE ROW', hot: false },
    { id: 2, title: 'Context attached', copy: 'STAGGER 034 MS', hot: true },
    { id: 3, title: 'Layout recomputed', copy: 'STATE OWNS ORDER', hot: false },
    { id: 4, title: 'Frame settled', copy: 'READY TO INTERRUPT', hot: false }
  ];
  @State stackCursor: number = 0;
  @State cardX: number = 0;
  @State cardY: number = 0;
  @State cardRotateX: number = 0;
  @State cardRotateY: number = 0;
  @State cardRotateZ: number = 0;
  @State cardScale: number = 1;
  @State cardOpacity: number = 1;
  @State isDragging: boolean = false;

  private navStack: NavPathStack = new NavPathStack();
  private nextRowId: number = 5;
  private chaosTimer: number = -1;
  private stackTimer: number = -1;
  private readonly stackItems: StackItem[] = [
    { index: '01', title: 'Spring handed.' },
    { index: '02', title: 'Velocity remembered.' },
    { index: '03', title: 'Depth resolved.' },
    { index: '04', title: 'Stack restored.' }
  ];

  aboutToDisappear(): void {
    if (this.chaosTimer >= 0) {
      clearInterval(this.chaosTimer);
      this.chaosTimer = -1;
    }
    if (this.stackTimer >= 0) {
      clearTimeout(this.stackTimer);
      this.stackTimer = -1;
    }
    this.navStack.clear();
  }

  private selectScene(index: number): void {
    this.selectedScene = index;
  }

  private openDetail(): void {
    this.getUIContext().animateTo({
      duration: 520,
      curve: curves.cubicBezierCurve(0.2, 0.8, 0.2, 1)
    }, () => {
      this.navStack.pushPath({ name: 'detail' }, false);
    });
  }

  private closeDetail(): void {
    this.getUIContext().animateTo({
      duration: 460,
      curve: curves.cubicBezierCurve(0.2, 0.8, 0.2, 1)
    }, () => {
      this.navStack.pop(false);
    });
  }

  private addRow(): void {
    const starts: string[] = ['Fresh signal', 'New layer', 'Input accepted', 'State appended'];
    const nextRows: MotionRow[] = this.rows.slice();
    const id: number = this.nextRowId++;
    nextRows.splice(Math.min(1, nextRows.length), 0, {
      id: id,
      title: starts[id % starts.length],
      copy: 'ENTERING FROM STATE',
      hot: id % 3 === 0
    });
    if (nextRows.length > 7) {
      nextRows.pop();
    }
    this.getUIContext().animateTo({
      duration: 340,
      curve: Curve.EaseOut
    }, () => {
      this.rows = nextRows;
    });
  }

  private removeRow(): void {
    if (this.rows.length <= 1) {
      return;
    }
    const nextRows: MotionRow[] = this.rows.slice();
    nextRows.splice(Math.max(0, nextRows.length - 2), 1);
    this.getUIContext().animateTo({
      duration: 340,
      curve: Curve.EaseOut
    }, () => {
      this.rows = nextRows;
    });
  }

  private triggerRapidRows(): void {
    if (this.chaosTimer >= 0) {
      clearInterval(this.chaosTimer);
    }
    let tick: number = 0;
    this.chaosTimer = setInterval(() => {
      if (tick % 2 === 0) {
        this.addRow();
      } else {
        this.removeRow();
      }
      tick += 1;
      if (tick >= 5) {
        if (this.chaosTimer >= 0) {
          clearInterval(this.chaosTimer);
          this.chaosTimer = -1;
        }
      }
    }, 90);
  }

  private resetStack(): void {
    if (this.stackTimer >= 0) {
      clearTimeout(this.stackTimer);
      this.stackTimer = -1;
    }
    this.getUIContext().animateTo({
      curve: curves.springMotion(0.45, 0.82)
    }, () => {
      this.cardX = 0;
      this.cardY = 0;
      this.cardRotateX = 0;
      this.cardRotateY = 0;
      this.cardRotateZ = 0;
      this.cardScale = 1;
      this.cardOpacity = 1;
      this.isDragging = false;
    });
  }

  private advanceStack(direction: number): void {
    if (this.stackTimer >= 0) {
      clearTimeout(this.stackTimer);
    }
    this.getUIContext().animateTo({
      duration: 340,
      curve: curves.cubicBezierCurve(0.15, 0.75, 0.25, 1)
    }, () => {
      this.cardX = direction * 380;
      this.cardY = -42;
      this.cardRotateX = 0;
      this.cardRotateY = direction * 18;
      this.cardRotateZ = direction * 24;
      this.cardOpacity = 0;
      this.cardScale = 0.94;
    });
    this.stackTimer = setTimeout(() => {
      this.stackCursor = (this.stackCursor + 1) % this.stackItems.length;
      this.cardScale = 0.92;
      this.cardOpacity = 0;
      this.cardX = 0;
      this.cardY = 20;
      this.cardRotateX = 0;
      this.cardRotateY = 0;
      this.cardRotateZ = 0;
      this.getUIContext().animateTo({
        duration: 220,
        curve: Curve.EaseOut
      }, () => {
        this.cardScale = 1;
        this.cardOpacity = 1;
        this.cardY = 0;
      });
      this.stackTimer = -1;
    }, 360);
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
  Kicker(text: string) {
    Text(text)
      .fontSize(8)
      .letterSpacing(1.3)
      .fontWeight(FontWeight.Bold)
      .fontColor('#FFB18C')
  }

  @Builder
  SharedOrb(size: number, radius: number, detail: boolean) {
    Stack({ alignContent: Alignment.Center }) {
      Row()
        .width(size * (detail ? 0.66 : 0.64))
        .height(size * (detail ? 0.66 : 0.64))
        .borderRadius(size)
        .border({ width: 1, color: 'rgba(215,255,87,0.55)' })
      Row()
        .width(size * 0.09)
        .height(size * 0.09)
        .borderRadius(size)
        .backgroundColor('#D7FF57')
        .shadow({ radius: 12, color: '#D7FF57' })
        .position({ x: size * 0.46, y: size * 0.08 })
      Row()
        .width(size * 0.30)
        .height(size * 0.30)
        .borderRadius(size * 0.12)
        .backgroundColor('#D7FF57')
        .rotate({ angle: 45 })
        .shadow({ radius: 24, color: 'rgba(215,255,87,0.35)' })
    }
    .width(size)
    .height(size)
    .borderRadius(radius)
    .backgroundColor('#111807')
    .geometryTransition('route-hero')
    .transition(TransitionEffect.OPACITY)
  }

  @Builder
  RouteScene() {
    Column() {
      Column({ space: 7 }) {
        this.Kicker('NAVIGATION / SHARED GEOMETRY')
        Text('One object,\ntwo pages.')
          .fontSize(31)
          .lineHeight(31)
          .fontColor('#F4F2E9')
      }
      .width('100%')
      .alignItems(HorizontalAlign.Start)

      Button() {
        Row({ space: 16 }) {
          this.SharedOrb(92, 27, false)
          Column({ space: 7 }) {
            Text('Shared signal').fontSize(17).fontColor('#F4F2E9').fontWeight(FontWeight.Medium)
            Text('TAP TO EXPAND').fontSize(8).letterSpacing(1.2).fontColor('#8C9190')
          }
          .alignItems(HorizontalAlign.Start)
        }
        .width('100%')
        .padding(14)
      }
      .width('100%')
      .height(138)
      .margin({ top: 30 })
      .backgroundColor('#121619')
      .border({ width: 1, color: 'rgba(255,255,255,0.11)' })
      .borderRadius(24)
      .onClick(() => this.openDetail())

      Text('The card frame and orbit retain one visual identity while Navigation moves the page context.')
        .fontSize(10)
        .lineHeight(15)
        .fontColor('#8C9190')
        .margin({ top: 22 })
    }
    .alignItems(HorizontalAlign.Start)
    .width('100%')
    .height('100%')
    .padding({ left: 20, right: 20, top: 23 })
  }

  @Builder
  DetailPage() {
    NavDestination() {
      Column() {
        Button('‹')
          .width(34)
          .height(34)
          .fontSize(18)
          .fontColor('#F4F2E9')
          .backgroundColor(Color.Transparent)
          .border({ width: 1, color: 'rgba(255,255,255,0.12)' })
          .borderRadius(17)
          .onClick(() => this.closeDetail())
        Column() {
          this.Kicker('ROUTE / DETAIL')
        }
        .margin({ top: 28 })
        Text('Context stays\ncontinuous.')
          .fontSize(31)
          .lineHeight(31)
          .fontColor('#F4F2E9')
          .margin({ top: 8 })
        Row({ space: 20 }) {
          this.SharedOrb(164, 42, true)
          Column({ space: 10 }) {
            Row().width('100%').height(3).borderRadius(3).backgroundColor('rgba(255,255,255,0.12)')
            Row().width('72%').height(3).borderRadius(3).backgroundColor('rgba(183,162,255,0.38)')
            Row().width('48%').height(3).borderRadius(3).backgroundColor('rgba(255,255,255,0.12)')
          }
          .layoutWeight(1)
        }
        .width('100%')
        .padding(16)
        .margin({ top: 28 })
        .backgroundColor('#121619')
        .border({ width: 1, color: 'rgba(255,255,255,0.11)' })
        .borderRadius(26)
        Row() {
          Text('IDENTITY LOCKED').fontSize(8).letterSpacing(1.1).fontColor('#8C9190')
          Blank()
          Text('03 / ROUTE').fontSize(8).letterSpacing(1.1).fontColor('#D7FF57')
        }
        .width('100%')
        .padding({ left: 4, right: 4, bottom: 13 })
        .margin({ top: 14 })
        .border({ width: { bottom: 1 }, color: 'rgba(255,255,255,0.11)' })
        Text('Push and pop run inside one explicit animated boundary so the shared element and page surface arrive together.')
          .fontSize(10)
          .lineHeight(15)
          .fontColor('#8C9190')
          .margin({ top: 14 })
      }
      .alignItems(HorizontalAlign.Start)
      .width('100%')
      .height('100%')
      .padding({ left: 20, right: 20, top: 20 })
      .backgroundColor('#0D1012')
    }
    .hideTitleBar(true)
    .systemTransition(NavigationSystemTransitionType.NONE)
    .backgroundColor('#0D1012')
  }

  @Builder
  PageMap(name: string) {
    if (name === 'detail') {
      this.DetailPage()
    }
  }

  @Builder
  RowItem(item: MotionRow, index: number) {
    Row({ space: 11 }) {
      Text(item.id.toString().padStart(2, '0'))
        .width(31)
        .height(31)
        .textAlign(TextAlign.Center)
        .fontSize(13)
        .fontColor(item.hot ? '#B7A2FF' : '#D7FF57')
        .backgroundColor(item.hot ? 'rgba(183,162,255,0.12)' : 'rgba(215,255,87,0.10)')
        .borderRadius(9)
      Column({ space: 2 }) {
        Text(item.title).fontSize(10).fontColor('#F4F2E9')
        Text(item.copy).fontSize(7).letterSpacing(0.7).fontColor('#8C9190')
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1)
      Row()
        .width(18)
        .height(3)
        .borderRadius(3)
        .backgroundColor(item.hot ? '#B7A2FF' : '#D7FF57')
    }
    .width('100%')
    .height(50)
    .padding({ left: 12, right: 12 })
    .backgroundColor(item.hot ? '#161326' : '#111518')
    .border({ width: 1, color: item.hot ? 'rgba(183,162,255,0.25)' : 'rgba(255,255,255,0.055)' })
    .borderRadius(16)
    .transition(TransitionEffect.OPACITY
      .combine(TransitionEffect.translate({ y: -14 }).animation({
        duration: 320,
        delay: index * 34,
        curve: Curve.EaseOut
      }))
      .combine(TransitionEffect.scale({ x: 0.94, y: 0.94 })))
  }

  @Builder
  ListScene() {
    Column() {
      Column({ space: 7 }) {
        this.Kicker('LIST / INTERRUPTIBLE')
        Text('Change without\na hard cut.')
          .fontSize(31)
          .lineHeight(31)
          .fontColor('#F4F2E9')
      }
      .width('100%')
      .alignItems(HorizontalAlign.Start)

      Row({ space: 7 }) {
        Button('ADD').height(28).padding({ left: 12, right: 12 }).fontSize(8)
          .fontColor('#D7FF57').backgroundColor(Color.Transparent)
          .border({ width: 1, color: 'rgba(215,255,87,0.28)' }).borderRadius(99)
          .onClick(() => this.addRow())
        Button('REMOVE').height(28).padding({ left: 12, right: 12 }).fontSize(8)
          .fontColor('#8C9190').backgroundColor(Color.Transparent)
          .border({ width: 1, color: 'rgba(255,255,255,0.12)' }).borderRadius(99)
          .onClick(() => this.removeRow())
        Button('RAPID').height(28).padding({ left: 12, right: 12 }).fontSize(8)
          .fontColor('#FFB18C').backgroundColor(Color.Transparent)
          .border({ width: 1, color: 'rgba(255,177,140,0.25)' }).borderRadius(99)
          .onClick(() => this.triggerRapidRows())
      }
      .width('100%')
      .margin({ top: 22 })

      List({ space: 7 }) {
        ForEach(this.rows, (item: MotionRow, index: number) => {
          ListItem() {
            this.RowItem(item, index)
          }
        }, (item: MotionRow) => item.id.toString())
      }
      .width('100%')
      .height(224)
      .margin({ top: 14 })
      .scrollBar(BarState.Off)

      Row() {
        Text(this.rows.length.toString().padStart(2, '0') + ' ROWS')
          .fontSize(8).letterSpacing(1.1).fontColor('#8C9190')
        Blank()
        Text('LAYOUT OWNED BY STATE')
          .fontSize(8).letterSpacing(1.1).fontColor('#8C9190')
      }
      .width('100%')
      .padding({ top: 11 })
      .border({ width: { top: 1 }, color: 'rgba(255,255,255,0.1)' })
    }
    .alignItems(HorizontalAlign.Start)
    .width('100%')
    .height('100%')
    .padding({ left: 20, right: 20, top: 23 })
  }

  @Builder
  StackScene() {
    Column() {
      Column({ space: 7 }) {
        this.Kicker('GESTURE / INERTIA')
        Text('Drag. Tilt.\nRelease.')
          .fontSize(31)
          .lineHeight(31)
          .fontColor('#F4F2E9')
      }
      .width('100%')
      .alignItems(HorizontalAlign.Start)

      Stack({ alignContent: Alignment.Center }) {
        Row()
          .width(242)
          .height(198)
          .borderRadius(25)
          .backgroundColor('#111518')
          .border({ width: 1, color: 'rgba(255,255,255,0.08)' })
          .translate({ y: 20 })
          .scale({ x: 0.90, y: 0.90 })
          .opacity(0.42)
        Row()
          .width(254)
          .height(206)
          .borderRadius(26)
          .backgroundColor('#121619')
          .border({ width: 1, color: 'rgba(255,255,255,0.09)' })
          .translate({ y: 10 })
          .scale({ x: 0.95, y: 0.95 })
          .opacity(0.68)
        Column() {
          Row() {
            Text(this.stackItems[this.stackCursor].index)
              .fontSize(23)
              .fontColor('#D7FF57')
              .fontFamily('serif')
            Blank()
            Text('03 / STACK').fontSize(7).letterSpacing(1.1).fontColor('#8C9190')
          }
          .width('100%')
          Stack({ alignContent: Alignment.Center }) {
            Row()
              .width(98)
              .height(98)
              .borderRadius(30)
              .border({ width: 1, color: 'rgba(215,255,87,0.24)' })
              .backgroundColor('rgba(215,255,87,0.055)')
            Row()
              .width(36)
              .height(36)
              .borderRadius(11)
              .border({ width: 1, color: '#D7FF57' })
              .rotate({ angle: 45 })
          }
          .height(100)
          Text(this.stackItems[this.stackCursor].title)
            .fontSize(15)
            .fontColor('#F4F2E9')
            .fontWeight(FontWeight.Medium)
          Text('DRAG OR FLING THE TOP CARD')
            .fontSize(7)
            .letterSpacing(1.0)
            .fontColor('#8C9190')
            .margin({ top: 7 })
        }
        .width(266)
        .height(218)
        .padding({ left: 18, right: 18, top: 16, bottom: 14 })
        .borderRadius(27)
        .backgroundColor(this.isDragging ? '#171B16' : '#141815')
        .border({ width: 1, color: this.isDragging ? 'rgba(215,255,87,0.30)' : 'rgba(255,255,255,0.10)' })
        .translate({ x: this.cardX, y: this.cardY })
        .rotate({ angle: this.cardRotateZ, centerX: '50%', centerY: '50%' })
        .scale({
          x: this.cardScale * (1 - Math.abs(this.cardRotateY) / 180),
          y: this.cardScale * (1 - Math.abs(this.cardRotateX) / 120)
        })
        .opacity(this.cardOpacity)
        .zIndex(3)
        .gesture(
          PanGesture({ fingers: 1, distance: 5 })
            .onActionStart(() => {
              if (this.stackTimer >= 0) {
                clearTimeout(this.stackTimer);
                this.stackTimer = -1;
              }
              this.isDragging = true;
            })
            .onActionUpdate((event: GestureEvent) => {
              this.cardX = event.offsetX;
              this.cardY = event.offsetY;
              this.cardRotateX = Math.max(-9, Math.min(9, -event.offsetY / 18));
              this.cardRotateY = Math.max(-16, Math.min(16, event.offsetX / 12));
              this.cardRotateZ = Math.max(-8, Math.min(8, event.offsetX / 28));
            })
            .onActionEnd((event: GestureEvent) => {
              if (!this.isDragging) {
                return;
              }
              this.isDragging = false;
              const direction: number = this.cardX !== 0 ? Math.sign(this.cardX) : Math.sign(event.velocityX || 1);
              if (Math.abs(this.cardX) > 110 || Math.abs(event.velocityX) > 600) {
                this.advanceStack(direction);
              } else {
                this.resetStack();
              }
            })
        )
      }
      .width('100%')
      .height(258)
      .margin({ top: 8 })

      Row() {
        Text('THRESHOLD 110').fontSize(8).letterSpacing(1.1).fontColor('#8C9190')
        Blank()
        Button('RESET').height(25).padding({ left: 10, right: 10 }).fontSize(8)
          .fontColor('#8C9190').backgroundColor(Color.Transparent)
          .border({ width: 1, color: 'rgba(255,255,255,0.12)' }).borderRadius(99)
          .onClick(() => this.resetStack())
      }
      .width('100%')
      .padding({ top: 10 })
      .border({ width: { top: 1 }, color: 'rgba(255,255,255,0.1)' })
    }
    .alignItems(HorizontalAlign.Start)
    .width('100%')
    .height('100%')
    .padding({ left: 20, right: 20, top: 23 })
  }

  @Builder
  LabContent() {
    Column() {
      Row() {
        Row({ space: 8 }) {
          Row().width(7).height(7).borderRadius(4).backgroundColor('#D7FF57').shadow({ radius: 10, color: '#D7FF57' })
          Text('MOTION LAB').fontSize(10).fontWeight(FontWeight.Bold).letterSpacing(1.8).fontColor('#F4F2E9')
        }
        Blank()
        Text('ARKUI / 03').fontSize(9).letterSpacing(1.6).fontColor('#8C9190')
      }
      .width('100%')
      .height(24)

      Column() {
        Text('ADVANCED MOTION STUDY').fontSize(8).letterSpacing(1.5).fontWeight(FontWeight.Bold).fontColor('#D7FF57')
        Text() {
          Span('Route.\n')
          Span('Reorder.\n').fontColor('#B7A2FF').fontFamily('serif')
          Span('Release.')
        }
        .fontSize(37)
        .lineHeight(31)
        .fontWeight(FontWeight.Medium)
        .fontColor('#F4F2E9')
        .margin({ top: 7 })
        Text('Shared route geometry, interruptible list choreography, and a spring-handed card stack.')
          .fontSize(10)
          .lineHeight(15)
          .fontColor('#8C9190')
          .width(315)
          .margin({ top: 9 })
      }
      .alignItems(HorizontalAlign.Start)
      .width('100%')
      .padding({ top: 17, bottom: 13 })

      Row({ space: 4 }) {
        this.SceneTab(0, '01 Route')
        this.SceneTab(1, '02 List')
        this.SceneTab(2, '03 Stack')
      }
      .width('100%')
      .padding(4)
      .backgroundColor('rgba(255,255,255,0.025)')
      .border({ width: 1, color: 'rgba(255,255,255,0.1)' })
      .borderRadius(99)

      Stack({ alignContent: Alignment.TopStart }) {
        if (this.selectedScene === 0) {
          this.RouteScene()
        } else if (this.selectedScene === 1) {
          this.ListScene()
        } else {
          this.StackScene()
        }
      }
      .width('100%')
      .layoutWeight(1)
      .margin({ top: 10 })
      .clip(true)
      .backgroundColor('#0D1012')
      .border({ width: 1, color: 'rgba(255,255,255,0.1)' })
      .borderRadius(27)

      Row() {
        Text('●  390 × 844').fontSize(8).letterSpacing(1.1).fontColor('rgba(255,255,255,0.32)')
        Text('60 FPS TARGET').fontSize(8).letterSpacing(1.1).fontColor('rgba(255,255,255,0.32)')
        Text('T+03').fontSize(8).letterSpacing(1.1).fontColor('rgba(255,255,255,0.32)')
      }
      .justifyContent(FlexAlign.SpaceBetween)
      .width('100%')
      .height(35)
    }
    .width('100%')
    .height('100%')
    .padding({ left: 20, right: 20, top: 12, bottom: 8 })
    .backgroundColor('#090C0E')
  }

  build() {
    Navigation(this.navStack) {
      this.LabContent()
    }
    .navDestination(this.PageMap)
    .hideTitleBar(true)
    .mode(NavigationMode.Stack)
    .width('100%')
    .height('100%')
    .backgroundColor('#090C0E')
  }
}
