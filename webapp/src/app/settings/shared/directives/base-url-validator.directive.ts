import { Directive } from '@angular/core';
import {
  AbstractControl,
  NG_VALIDATORS,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';

@Directive({
  selector: '[appBaseUrlValidator]',
  providers: [
    {
      provide: NG_VALIDATORS,
      useExisting: BaseUrlValidatorDirective,
      multi: true,
    },
  ],
})
export class BaseUrlValidatorDirective implements Validators {
  validate(control: AbstractControl): ValidationErrors | null {
    return baseUrlValidator()(control);
  }
}

export function baseUrlValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = control.value as string;
    const lines = value
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => !!line);
    const invalidValues = lines.filter(
      (line) => !/^https?:\/\/\S+$/.test(line)
    );
    return invalidValues.length > 0
      ? { baseUrl: { value: invalidValues } }
      : null;
  };
}
