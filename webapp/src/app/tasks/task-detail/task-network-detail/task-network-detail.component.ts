import {
  Component,
  ChangeDetectionStrategy,
  Input,
  ChangeDetectorRef,
  OnChanges,
} from '@angular/core';

import { EChartsOption } from 'echarts';

import { RunningStatus, TaskStatus } from '../../shared/task.model';
import { toBitRateString } from '../../../shared/utils';

interface ChartDataItem {
  name: string;
  value: [string, number];
}

@Component({
  selector: 'app-task-network-detail',
  templateUrl: './task-network-detail.component.html',
  styleUrls: ['./task-network-detail.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TaskNetworkDetailComponent implements OnChanges {
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
        // text: '下载速度',
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
              <div>${toBitRateString(param.value[1])}</div>
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
        name: '下载速度',
        // boundaryGap: [0, '100%'],
        splitLine: {
          show: true,
        },
        axisLabel: {
          formatter: function (value: number) {
            return toBitRateString(value);
          },
        },
      },
      series: [
        {
          name: '下载速度',
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
      value: [date.toISOString(), this.taskStatus.dl_rate * 8],
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
