import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { LayoutModule } from '@angular/cdk/layout';
import { ClipboardModule } from '@angular/cdk/clipboard';

import { NzGridModule } from 'ng-zorro-antd/grid';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzAvatarModule } from 'ng-zorro-antd/avatar';
import { NzSkeletonModule } from 'ng-zorro-antd/skeleton';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzCheckboxModule } from 'ng-zorro-antd/checkbox';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzProgressModule } from 'ng-zorro-antd/progress';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzStatisticModule } from 'ng-zorro-antd/statistic';
import { NzDescriptionsModule } from 'ng-zorro-antd/descriptions';
import { NgxEchartsModule } from 'ngx-echarts';

import { SharedModule } from '../shared/shared.module';
import { TasksRoutingModule } from './tasks-routing.module';
import { TasksComponent } from './tasks.component';
import { ToolbarComponent } from './toolbar/toolbar.component';
import { TaskListComponent } from './task-list/task-list.component';
import { TaskItemComponent } from './task-item/task-item.component';
import { FilterTasksPipe } from './shared/pipes/filter-tasks.pipe';
import { AddTaskDialogComponent } from './add-task-dialog/add-task-dialog.component';
import { TaskSettingsDialogComponent } from './task-settings-dialog/task-settings-dialog.component';
import { StatusDisplayComponent } from './status-display/status-display.component';
import { TaskDetailComponent } from './task-detail/task-detail.component';
import { TaskFileDetailComponent } from './task-detail/task-file-detail/task-file-detail.component';
import { TaskUserInfoDetailComponent } from './task-detail/task-user-info-detail/task-user-info-detail.component';
import { TaskRoomInfoDetailComponent } from './task-detail/task-room-info-detail/task-room-info-detail.component';
import { TaskPostprocessingDetailComponent } from './task-detail/task-postprocessing-detail/task-postprocessing-detail.component';
import { TaskRecordingDetailComponent } from './task-detail/task-recording-detail/task-recording-detail.component';
import { TaskNetworkDetailComponent } from './task-detail/task-network-detail/task-network-detail.component';
import { InfoPanelComponent } from './info-panel/info-panel.component';
import { WaveGraphComponent } from './info-panel/wave-graph/wave-graph.component';

@NgModule({
  declarations: [
    TasksComponent,
    ToolbarComponent,
    TaskListComponent,
    TaskItemComponent,
    FilterTasksPipe,
    AddTaskDialogComponent,
    TaskSettingsDialogComponent,
    StatusDisplayComponent,
    TaskDetailComponent,
    TaskFileDetailComponent,
    TaskUserInfoDetailComponent,
    TaskRoomInfoDetailComponent,
    TaskPostprocessingDetailComponent,
    TaskRecordingDetailComponent,
    TaskNetworkDetailComponent,
    InfoPanelComponent,
    WaveGraphComponent,
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    LayoutModule,
    ClipboardModule,

    NzGridModule,
    NzCardModule,
    NzSkeletonModule,
    NzAvatarModule,
    NzIconModule,
    NzSkeletonModule,
    NzToolTipModule,
    NzTagModule,
    NzSwitchModule,
    NzDropDownModule,
    NzButtonModule,
    NzModalModule,
    NzFormModule,
    NzInputModule,
    NzCheckboxModule,
    NzPopconfirmModule,
    NzRadioModule,
    NzDividerModule,
    NzEmptyModule,
    NzSpinModule,
    NzAlertModule,
    NzDrawerModule,
    NzSelectModule,
    NzProgressModule,
    NzTableModule,
    NzStatisticModule,
    NzDescriptionsModule,
    NgxEchartsModule.forRoot({
      echarts: () => import('echarts'),
    }),

    TasksRoutingModule,
    SharedModule,
  ],
})
export class TasksModule {}
