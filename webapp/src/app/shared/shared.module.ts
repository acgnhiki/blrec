import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzPageHeaderModule } from 'ng-zorro-antd/page-header';

import { DataurlPipe } from './pipes/dataurl.pipe';
import { DurationPipe } from './pipes/duration.pipe';
import { DataratePipe } from './pipes/datarate.pipe';
import { FilesizePipe } from './pipes/filesize.pipe';
import { QualityPipe } from './pipes/quality.pipe';
import { ProgressPipe } from './pipes/progress.pipe';
import { FilenamePipe } from './pipes/filename.pipe';
import { PageSectionComponent } from './components/page-section/page-section.component';
import { SubPageComponent } from './components/sub-page/sub-page.component';
import { SubPageContentDirective } from './directives/sub-page-content.directive';
import { FilestatusPipe } from './pipes/filestatus.pipe';

@NgModule({
  declarations: [
    DataurlPipe,
    DurationPipe,
    DataratePipe,
    FilesizePipe,
    QualityPipe,
    SubPageComponent,
    SubPageContentDirective,
    PageSectionComponent,
    ProgressPipe,
    FilenamePipe,
    FilestatusPipe,
  ],
  imports: [CommonModule, NzSpinModule, NzPageHeaderModule],
  exports: [
    DataurlPipe,
    DurationPipe,
    DataratePipe,
    FilesizePipe,
    QualityPipe,
    ProgressPipe,
    FilenamePipe,

    SubPageComponent,
    SubPageContentDirective,
    PageSectionComponent,
    FilestatusPipe,
  ],
})
export class SharedModule {}
