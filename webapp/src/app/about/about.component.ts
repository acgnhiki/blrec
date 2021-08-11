import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { AppInfo } from '../core/models/app.models';

@Component({
  selector: 'app-about',
  templateUrl: './about.component.html',
  styleUrls: ['./about.component.scss'],
})
export class AboutComponent implements OnInit {
  appInfo!: AppInfo;

  constructor(
    private changeDetector: ChangeDetectorRef,
    private route: ActivatedRoute
  ) {}
  ngOnInit(): void {
    this.route.data.subscribe((data) => {
      this.appInfo = data.appInfo;
      this.changeDetector.markForCheck();
    });
  }
}
