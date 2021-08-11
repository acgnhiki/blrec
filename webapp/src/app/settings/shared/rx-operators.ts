import { AbstractControl } from '@angular/forms';

import { pipe } from 'rxjs';
import {
  debounceTime,
  distinctUntilChanged,
  filter,
  map,
  tap,
} from 'rxjs/operators';
import isEqual from 'lodash-es/isEqual';
import isString from 'lodash-es/isString';
import transform from 'lodash-es/transform';

export function filterValueChanges<T extends object>(control: AbstractControl) {
  return pipe(
    filter<T>(() => control.valid),
    debounceTime(300),
    trimString(),
    distinctUntilChanged<T>(isEqual)
  );
}

export function trimString<T extends object>() {
  return pipe(
    map(
      (object: T) =>
        transform(
          object,
          (result, value: any, prop) => {
            result[prop] = isString(value) ? value.trim() : value;
          },
          {} as T
        ) as T
    )
  );
}

export function debugValueChanges<T>() {
  return pipe(
    tap((value: T) => {
      console.debug('value change:', value);
    })
  );
}
