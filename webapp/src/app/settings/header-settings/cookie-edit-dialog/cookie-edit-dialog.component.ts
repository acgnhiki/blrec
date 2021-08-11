import {
  Component,
  ChangeDetectionStrategy,
  Input,
  Output,
  ChangeDetectorRef,
  EventEmitter,
  OnChanges,
} from '@angular/core';
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';

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
    private changeDetector: ChangeDetectorRef
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
}
