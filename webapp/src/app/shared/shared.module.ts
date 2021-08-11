import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzPageHeaderModule } from 'ng-zorro-antd/page-header';

import { DataurlPipe } from './pipes/dataurl.pipe';
import { DurationPipe } from './pipes/duration.pipe';
import { SpeedPipe } from './pipes/speed.pipe';
import { FilesizePipe } from './pipes/filesize.pipe';
import { QualityPipe } from './pipes/quality.pipe';
import { ProgressPipe } from './pipes/progress.pipe';
import { FilenamePipe } from './pipes/filename.pipe';
import { PageSectionComponent } from './components/page-section/page-section.component';
import { SubPageComponent } from './components/sub-page/sub-page.component';
import { SubPageContentDirective } from './directives/sub-page-content.directive';

@NgModule({
  declarations: [
    DataurlPipe,
    DurationPipe,
    SpeedPipe,
    FilesizePipe,
    QualityPipe,
    SubPageComponent,
    SubPageContentDirective,
    PageSectionComponent,
    ProgressPipe,
    FilenamePipe,
  ],
  imports: [
    CommonModule,
    NzSpinModule,
    NzPageHeaderModule,
  ],
  exports: [
    DataurlPipe,
    DurationPipe,
    SpeedPipe,
    FilesizePipe,
    QualityPipe,
    ProgressPipe,
    FilenamePipe,

    SubPageComponent,
    SubPageContentDirective,
    PageSectionComponent,
  ]
})
export class SharedModule { }
