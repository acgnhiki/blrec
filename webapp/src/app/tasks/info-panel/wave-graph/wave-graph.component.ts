import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
  ChangeDetectorRef,
  OnDestroy,
} from '@angular/core';

import { interval, Subscription } from 'rxjs';

interface Point {
  x: number;
  y: number;
}

@Component({
  selector: 'app-wave-graph',
  templateUrl: './wave-graph.component.svg',
  styleUrls: ['./wave-graph.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WaveGraphComponent implements OnInit, OnDestroy {
  @Input() value: number = 0;
  @Input() width: number = 200;
  @Input() height: number = 16;
  @Input() stroke: string = 'white';

  private data: number[] = [];
  private points: Point[] = [];
  private subscription?: Subscription;

  constructor(private changeDetector: ChangeDetectorRef) {
    for (let x = 0; x <= this.width; x += 2) {
      this.data.push(0);
      this.points.push({ x: x, y: this.height });
    }
  }

  get polylinePoints(): string {
    return this.points.map((p) => `${p.x},${p.y}`).join(' ');
  }

  ngOnInit(): void {
    this.subscription = interval(1000).subscribe(() => {
      this.data.push(this.value || 0);
      this.data.shift();

      let maximum = Math.max(...this.data);
      this.points = this.data.map((value, index) => ({
        x: Math.min(index * 2, this.width),
        y: (1 - value / (maximum || 1)) * this.height,
      }));

      this.changeDetector.markForCheck();
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }
}
