import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
} from '@angular/core';
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';

import { NzMessageService } from 'ng-zorro-antd/message';

import { ValidationService } from 'src/app/core/services/validation.service';

@Component({
  selector: 'app-cookie-edit-dialog',
  templateUrl: './cookie-edit-dialog.component.html',
  styleUrls: ['./cookie-edit-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CookieEditDialogComponent implements OnChanges {
  @Input() value = '';
  @Input() visible = false;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() cancel = new EventEmitter<undefined>();
  @Output() confirm = new EventEmitter<string>();

  readonly settingsForm: FormGroup;
  readonly warningTip =
    '全部任务都需重启弹幕客户端才能生效，正在录制的任务可能会丢失弹幕！';

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef,
    private validationService: ValidationService,
    private message: NzMessageService
  ) {
    this.settingsForm = formBuilder.group({
      cookie: [''],
    });
  }

  get control() {
    return this.settingsForm.get('cookie') as FormControl;
  }

  ngOnChanges(): void {
    this.setValue();
  }

  open(): void {
    this.setValue();
    this.setVisible(true);
  }

  close(): void {
    this.setVisible(false);
  }

  setVisible(visible: boolean): void {
    this.visible = visible;
    this.visibleChange.emit(visible);
    this.changeDetector.markForCheck();
  }

  setValue(): void {
    this.control.setValue(this.value);
    this.changeDetector.markForCheck();
  }

  handleCancel(): void {
    this.cancel.emit();
    this.close();
  }

  handleConfirm(): void {
    this.confirm.emit(this.control.value.trim());
    this.close();
  }

  testCookie(): void {
    this.validationService
      .validateCookie(this.control.value)
      .subscribe((result) => {
        if (result.code === 0) {
          this.message.success(
            `uid: ${result.data?.mid}, uname: ${result.data?.uname}`
          );
        } else {
          this.message.error(`${result.code}: ${result.message}`);
        }
      });
  }
}
