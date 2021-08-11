import { Component, ChangeDetectionStrategy, Input } from '@angular/core';

import { Observable } from 'rxjs';

import { AppInfo } from 'src/app/core/models/app.models';
import { UpdateService } from 'src/app/core/services/update.service';

@Component({
  selector: 'app-info-list',
  templateUrl: './info-list.component.html',
  styleUrls: ['./info-list.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InfoListComponent {
  @Input() appInfo!: AppInfo;

  latestVesion$: Observable<string>;

  constructor(updateService: UpdateService) {
    this.latestVesion$ = updateService.getLatestVerisonString();
  }
}
