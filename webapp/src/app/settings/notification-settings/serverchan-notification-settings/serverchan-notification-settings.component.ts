import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import pick from 'lodash-es/pick';

import {
  KEYS_OF_NOTIFICATION_SETTINGS,
  KEYS_OF_NOTIFIER_SETTINGS,
  KEYS_OF_SERVERCHAN_SETTINGS,
  NotificationSettings,
  NotifierSettings,
  ServerchanNotificationSettings,
  ServerchanSettings,
} from '../../shared/setting.model';

@Component({
  selector: 'app-serverchan-notification-settings',
  templateUrl: './serverchan-notification-settings.component.html',
  styleUrls: ['./serverchan-notification-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ServerchanNotificationSettingsComponent implements OnInit {
  serverchanSettings!: ServerchanSettings;
  notifierSettings!: NotifierSettings;
  notificationSettings!: NotificationSettings;

  constructor(
    private changeDetector: ChangeDetectorRef,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.route.data.subscribe((data) => {
      const settings = data.settings as ServerchanNotificationSettings;
      this.serverchanSettings = pick(settings, KEYS_OF_SERVERCHAN_SETTINGS);
      this.notifierSettings = pick(settings, KEYS_OF_NOTIFIER_SETTINGS);
      this.notificationSettings = pick(settings, KEYS_OF_NOTIFICATION_SETTINGS);
      this.changeDetector.markForCheck();
    });
  }
}
