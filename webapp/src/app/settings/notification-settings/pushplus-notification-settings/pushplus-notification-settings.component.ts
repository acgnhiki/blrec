import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import pick from 'lodash-es/pick';

import {
  NotificationSettings,
  PushplusSettings,
  NotifierSettings,
  PushplusNotificationSettings,
  KEYS_OF_PUSHPLUS_SETTINGS,
  KEYS_OF_NOTIFIER_SETTINGS,
  KEYS_OF_NOTIFICATION_SETTINGS,
} from '../../shared/setting.model';

@Component({
  selector: 'app-pushplus-notification-settings',
  templateUrl: './pushplus-notification-settings.component.html',
  styleUrls: ['./pushplus-notification-settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PushplusNotificationSettingsComponent implements OnInit {
  pushplusSettings!: PushplusSettings;
  notifierSettings!: NotifierSettings;
  notificationSettings!: NotificationSettings;

  constructor(
    private changeDetector: ChangeDetectorRef,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.route.data.subscribe((data) => {
      const settings = data.settings as PushplusNotificationSettings;
      this.changeDetector.markForCheck();
      this.pushplusSettings = pick(settings, KEYS_OF_PUSHPLUS_SETTINGS);
      this.notifierSettings = pick(settings, KEYS_OF_NOTIFIER_SETTINGS);
      this.notificationSettings = pick(settings, KEYS_OF_NOTIFICATION_SETTINGS);
    });
  }
}
