import {
  Component,
  ChangeDetectionStrategy,
  forwardRef,
  OnInit,
} from '@angular/core';
import {
  ControlValueAccessor,
  FormBuilder,
  FormControl,
  FormGroup,
  NG_VALUE_ACCESSOR,
  Validators,
} from '@angular/forms';

import { OnChangeType, OnTouchedType } from 'ng-zorro-antd/core/types';

import { formatDuration, parseDuration } from '../../../shared/utils';
import { filterValueChanges } from 'src/app/settings/shared/rx-operators';

@Component({
  selector: 'app-input-duration',
  templateUrl: './input-duration.component.html',
  styleUrls: ['./input-duration.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputDurationComponent),
      multi: true,
    },
  ],
})
export class InputDurationComponent implements OnInit, ControlValueAccessor {
  readonly formGroup: FormGroup;
  private value: number = 0;

  onChange: OnChangeType = () => {};
  onTouched: OnTouchedType = () => {};

  constructor(formBuilder: FormBuilder) {
    this.formGroup = formBuilder.group({
      duration: [
        '',
        [Validators.required, Validators.pattern(/^\d{2}:[0-5]\d:[0-5]\d$/)],
      ],
    });
  }

  get durationControl() {
    return this.formGroup.get('duration') as FormControl;
  }

  ngOnInit(): void {
    this.durationControl.valueChanges
      .pipe(filterValueChanges(this.durationControl))
      .subscribe((displayValue) => {
        this.onDisplayValueChange(displayValue);
      });
  }

  writeValue(value: number): void {
    if (typeof value === 'number' && value >= 0) {
      this.value = value;
      this.updateDisplayValue(value);
    }
  }

  registerOnChange(fn: OnChangeType): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: OnTouchedType): void {
    this.onTouched = fn;
  }

  setDisabledState(disabled: boolean): void {
    if (disabled) {
      this.durationControl.disable();
    } else {
      this.durationControl.enable();
    }
  }

  private onDisplayValueChange(displayValue: string): void {
    const value = parseDuration(displayValue);
    if (typeof value === 'number' && this.value !== value) {
      this.value = value;
      this.onChange(value);
    }
  }

  private updateDisplayValue(value: number): void {
    const displayValue = formatDuration(value);
    this.durationControl.setValue(displayValue);
  }
}
