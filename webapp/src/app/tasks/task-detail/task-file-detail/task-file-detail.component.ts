import {
  Component,
  ChangeDetectionStrategy,
  Input,
  OnChanges,
} from '@angular/core';

import {
  NzTableSortFn,
  NzTableSortOrder,
  NzTableFilterFn,
  NzTableFilterList,
} from 'ng-zorro-antd/table';

import {
  DanmakuFileDetail,
  VideoFileDetail,
  VideoFileStatus,
} from '../../shared/task.model';

type FileDetail = VideoFileDetail | DanmakuFileDetail;
interface ColumnItem {
  name: string;
  sortFn: NzTableSortFn<FileDetail> | null;
  sortOrder: NzTableSortOrder | null;
  sortDirections: NzTableSortOrder[];
  filterFn: NzTableFilterFn<FileDetail> | null;
  listOfFilter: NzTableFilterList;
  filterMultiple: boolean;
}

const OrderedStatuses = [
  VideoFileStatus.RECORDING,
  VideoFileStatus.INJECTING,
  VideoFileStatus.REMUXING,
  VideoFileStatus.COMPLETED,
  VideoFileStatus.MISSING,
];

@Component({
  selector: 'app-task-file-detail',
  templateUrl: './task-file-detail.component.html',
  styleUrls: ['./task-file-detail.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TaskFileDetailComponent implements OnChanges {
  @Input() loading: boolean = true;
  @Input() videoFileDetails: VideoFileDetail[] = [];
  @Input() danmakuFileDetails: DanmakuFileDetail[] = [];

  readonly VideoFileStatus = VideoFileStatus;

  fileDetails: FileDetail[] = [];

  columns: ColumnItem[] = [
    {
      name: '文件',
      sortOrder: 'ascend',
      sortFn: (a: FileDetail, b: FileDetail) => a.path.localeCompare(b.path),
      sortDirections: ['ascend', 'descend'],
      filterMultiple: false,
      listOfFilter: [
        { text: '视频', value: 'video' },
        { text: '弹幕', value: 'danmaku' },
      ],
      filterFn: (value: string, item: FileDetail) => {
        switch (value) {
          case 'video':
            return item.path.endsWith('.flv') || item.path.endsWith('.mp4');
          case 'danmaku':
            return item.path.endsWith('.xml');
          default:
            return false;
        }
      },
    },
    {
      name: '大小',
      sortOrder: null,
      sortFn: (a: FileDetail, b: FileDetail) => a.size - b.size,
      sortDirections: ['ascend', 'descend', null],
      filterMultiple: true,
      listOfFilter: [],
      filterFn: null,
    },
    {
      name: '状态',
      sortOrder: null,
      sortFn: (a: FileDetail, b: FileDetail) =>
        OrderedStatuses.indexOf(a.status as VideoFileStatus) -
        OrderedStatuses.indexOf(b.status as VideoFileStatus),
      sortDirections: ['ascend', 'descend', null],
      filterMultiple: true,
      listOfFilter: [
        { text: '录制中', value: [VideoFileStatus.RECORDING] },
        {
          text: '处理中',
          value: [VideoFileStatus.INJECTING, VideoFileStatus.REMUXING],
        },
        { text: '已完成', value: [VideoFileStatus.COMPLETED] },
        { text: '不存在', value: [VideoFileStatus.MISSING] },
      ],
      filterFn: (filterValues: VideoFileStatus[][], item: FileDetail) =>
        filterValues.some((listOfStatus) =>
          listOfStatus.some((status) => status === item.status)
        ),
    },
  ];

  constructor() {}

  ngOnChanges() {
    this.fileDetails = [...this.videoFileDetails, ...this.danmakuFileDetails];
  }

  trackByPath(index: number, data: FileDetail): string {
    return data.path;
  }
}
