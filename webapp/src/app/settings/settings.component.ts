import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnInit,
  ViewChild,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { NGXLogger } from 'ngx-logger';

import { RouterScrollService } from '../core/services/router-scroll.service';
import { Settings } from './shared/setting.model';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss'],
})
export class SettingsComponent implements OnInit, AfterViewInit {
  settings!: Settings;

  @ViewChild('innerContent')
  private innerContent!: ElementRef<HTMLElement>;

  constructor(
    private changeDetector: ChangeDetectorRef,
    private route: ActivatedRoute,
    private logger: NGXLogger,
    private routerScrollService: RouterScrollService
  ) {}

  ngOnInit(): void {
    this.route.data.subscribe((data) => {
      this.settings = data.settings;
      this.changeDetector.markForCheck();
    });
  }

  ngAfterViewInit() {
    if (this.innerContent) {
      this.routerScrollService.setCustomViewportToScroll(
        this.innerContent.nativeElement
      );
    } else {
      this.logger.error('The content element could not be found!');
    }
  }
}
