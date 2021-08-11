import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { tap } from 'rxjs/operators';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalService } from 'ng-zorro-antd/modal';

import { retry } from '../../../shared/rx-operators';
import { SettingService } from '../../shared/services/setting.service';
import { WebhookSettings } from '../../shared/setting.model';

@Component({
  selector: 'app-webhook-manager',
  templateUrl: './webhook-manager.component.html',
  styleUrls: ['./webhook-manager.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WebhookManagerComponent implements OnInit {
  static readonly MAX_WEBHOOKS = 50;

  webhooks!: WebhookSettings[];

  dialogTitle = '';
  dialogOkButtonText = '';
  dialogVisible = false;
  editingIndex = -1;
  editingSettings?: WebhookSettings;

  constructor(
    private changeDetector: ChangeDetectorRef,
    private route: ActivatedRoute,
    private message: NzMessageService,
    private modal: NzModalService,
    private settingService: SettingService
  ) {}

  get canAdd() {
    return this.webhooks.length < WebhookManagerComponent.MAX_WEBHOOKS;
  }

  ngOnInit(): void {
    this.route.data.subscribe((data) => {
      this.webhooks = data.settings;
      this.changeDetector.markForCheck();
    });
  }

  addWebhook(): void {
    this.editingIndex = -1;
    this.editingSettings = undefined;
    this.dialogTitle = '添加 webhook';
    this.dialogOkButtonText = '添加';
    this.dialogVisible = true;
  }

  removeWebhook(index: number): void {
    const webhooks = this.webhooks.filter((v, i) => i !== index);
    this.changeSettings(webhooks).subscribe(() => this.reset());
  }

  editWebhook(index: number): void {
    this.editingIndex = index;
    this.editingSettings = { ...this.webhooks[index] };
    this.dialogTitle = '修改 webhook';
    this.dialogOkButtonText = '保存';
    this.dialogVisible = true;
  }

  clearWebhook(): void {
    this.modal.confirm({
      nzTitle: '确定要清空 Webhook ？',
      nzOnOk: () =>
        new Promise((resolve, reject) => {
          this.changeSettings([]).subscribe(resolve, reject);
        }),
    });
  }

  onDialogCanceled(): void {
    this.reset();
  }

  onDialogConfirmed(settings: WebhookSettings): void {
    let webhooks;
    if (this.editingIndex === -1) {
      webhooks = [...this.webhooks, settings];
    } else {
      webhooks = [...this.webhooks];
      webhooks[this.editingIndex] = settings;
    }
    this.changeSettings(webhooks).subscribe(() => this.reset());
  }

  private reset(): void {
    this.editingIndex = -1;
    delete this.editingSettings;
  }

  private changeSettings(settings: WebhookSettings[]) {
    return this.settingService.changeSettings({ webhooks: settings }).pipe(
      retry(3, 300),
      tap(
        (settings) => {
          this.webhooks = settings['webhooks']!;
          this.changeDetector.markForCheck();
        },
        (error: HttpErrorResponse) => {
          this.message.error(`Webhook 设置出错: ${error.message}`);
        }
      )
    );
  }
}
