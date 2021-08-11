import { pipe, timer } from 'rxjs';
import { delayWhen, retryWhen } from 'rxjs/operators';

/**
 * retry operator
 * @param count the number of retries, use Number.POSITIVE_INFINITY to infinitely retry.
 * @param delay time to dealy, in milliseconds.
 * @returns
 */
export function retry<T>(count: number, delay: number) {
  return pipe(
    retryWhen<T>((errors) =>
      errors.pipe(
        delayWhen((value, index) => {
          if (count !== Number.POSITIVE_INFINITY && index >= count) {
            throw value;
          }
          return timer(delay);
        })
      )
    )
  );
}
