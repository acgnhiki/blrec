import {
  Component,
  ChangeDetectionStrategy,
  Input,
  Output,
  ChangeDetectorRef,
  EventEmitter,
  OnChanges,
} from '@angular/core';
import {
  FormBuilder,
  FormControl,
  FormGroup,
  Validators,
} from '@angular/forms';
import {
  BASE_LIVE_API_URL_DEFAULT,
  BASE_URL_PATTERN,
} from '../../shared/constants/form';

@Component({
  selector: 'app-base-live-api-url-edit-dialog',
  templateUrl: './base-live-api-url-edit-dialog.component.html',
  styleUrls: ['./base-live-api-url-edit-dialog.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BaseLiveApiUrlEditDialogComponent implements OnChanges {
  @Input() value = '';
  @Input() visible = false;
  @Output() visibleChange = new EventEmitter<boolean>();
  @Output() cancel = new EventEmitter<undefined>();
  @Output() confirm = new EventEmitter<string>();

  readonly settingsForm: FormGroup;
  readonly defaultBaseLiveApiUrl = BASE_LIVE_API_URL_DEFAULT;

  constructor(
    formBuilder: FormBuilder,
    private changeDetector: ChangeDetectorRef
  ) {
    this.settingsForm = formBuilder.group({
      baseLiveApiUrl: [
        '',
        [Validators.required, Validators.pattern(BASE_URL_PATTERN)],
      ],
    });
  }

  get control() {
    return this.settingsForm.get('baseLiveApiUrl') as FormControl;
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

  restoreDefault(): void {
    this.control.setValue(this.defaultBaseLiveApiUrl);
  }
}
