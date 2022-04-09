import {
  Component,
  ChangeDetectionStrategy,
  Input,
  ChangeDetectorRef,
  OnChanges,
} from '@angular/core';

import { EChartsOption } from 'echarts';

import { RunningStatus, TaskStatus } from '../../shared/task.model';
import { toByteRateString } from '../../../shared/utils';

interface ChartDataItem {
  name: string;
  value: [string, number];
}

@Component({
  selector: 'app-task-recording-detail',
  templateUrl: './task-recording-detail.component.html',
  styleUrls: ['./task-recording-detail.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TaskRecordingDetailComponent implements OnChanges {
  @Input() loading: boolean = true;
  @Input() taskStatus!: TaskStatus;

  initialChartOptions: EChartsOption = {};
  updatedChartOptions: EChartsOption = {};

  private chartData: ChartDataItem[] = [];

  constructor(private changeDetector: ChangeDetectorRef) {
    this.initChartOptions();
  }

  ngOnChanges(): void {
    if (this.taskStatus.running_status === RunningStatus.RECORDING) {
      this.updateChartOptions();
    }
  }

  private initChartOptions(): void {
    const timestamp = Date.now();

    for (let i = 60 - 1; i >= 0; i--) {
      const date = new Date(timestamp - i * 1000);
      this.chartData.push({
        name: date.toLocaleString('zh-CN', { hour12: false }),
        value: [date.toISOString(), 0],
      });
    }

    this.initialChartOptions = {
      title: {
        // text: '录制速度',
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const param = params[0] as ChartDataItem;
          return `
            <div>
              <div>
                ${new Date(param.name).toLocaleTimeString('zh-CN', {
                  hour12: false,
                })}
              </div>
              <div>${toByteRateString(param.value[1])}</div>
            </div>
          `;
        },
        axisPointer: {
          animation: false,
        },
      },
      xAxis: {
        type: 'time',
        name: '时间',
        min: 'dataMin',
        max: 'dataMax',
        splitLine: {
          show: true,
        },
      },
      yAxis: {
        type: 'value',
        name: '录制速度',
        // boundaryGap: [0, '100%'],
        splitLine: {
          show: true,
        },
        axisLabel: {
          formatter: (value: number) => {
            return toByteRateString(value);
          },
        },
      },
      series: [
        {
          name: '录制速度',
          type: 'line',
          showSymbol: false,
          smooth: true,
          lineStyle: {
            width: 1,
          },
          areaStyle: {
            opacity: 0.2,
          },
          data: this.chartData,
        },
      ],
    };
  }

  private updateChartOptions(): void {
    const date = new Date();
    this.chartData.push({
      name: date.toLocaleString('zh-CN', { hour12: false }),
      value: [date.toISOString(), this.taskStatus.rec_rate],
    });
    this.chartData.shift();

    this.updatedChartOptions = {
      series: [
        {
          data: this.chartData,
        },
      ],
    };

    this.changeDetector.markForCheck();
  }
}
