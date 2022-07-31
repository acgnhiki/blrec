import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';

import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzPageHeaderModule } from 'ng-zorro-antd/page-header';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';

import { DataurlPipe } from './pipes/dataurl.pipe';
import { DurationPipe } from './pipes/duration.pipe';
import { DataratePipe } from './pipes/datarate.pipe';
import { FilesizePipe } from './pipes/filesize.pipe';
import { QualityPipe } from './pipes/quality.pipe';
import { ProgressPipe } from './pipes/progress.pipe';
import { FilenamePipe } from './pipes/filename.pipe';
import { FilestatusPipe } from './pipes/filestatus.pipe';
import { SubPageContentDirective } from './directives/sub-page-content.directive';
import { PageSectionComponent } from './components/page-section/page-section.component';
import { SubPageComponent } from './components/sub-page/sub-page.component';
import { InputFilesizeComponent } from './components/input-filesize/input-filesize.component';
import { InputDurationComponent } from './components/input-duration/input-duration.component';

@NgModule({
  declarations: [
    DataurlPipe,
    DurationPipe,
    DataratePipe,
    FilesizePipe,
    QualityPipe,
    ProgressPipe,
    FilenamePipe,
    FilestatusPipe,
    SubPageContentDirective,
    SubPageComponent,
    PageSectionComponent,
    InputFilesizeComponent,
    InputDurationComponent,
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    NzSpinModule,
    NzFormModule,
    NzPageHeaderModule,
    NzInputModule,
  ],
  exports: [
    DataurlPipe,
    DurationPipe,
    DataratePipe,
    FilesizePipe,
    QualityPipe,
    ProgressPipe,
    FilenamePipe,
    FilestatusPipe,
    SubPageContentDirective,
    SubPageComponent,
    PageSectionComponent,
    InputFilesizeComponent,
    InputDurationComponent,
  ],
})
export class SharedModule {}
