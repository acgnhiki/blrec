import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'duration',
})
export class DurationPipe implements PipeTransform {
  transform(totalSeconds: number): string {
    if (totalSeconds < 0) {
      throw RangeError(
        'the argument totalSeconds must be greater than or equal to 0'
      );
    }

    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds / 60) % 60);
    const seconds = Math.floor(totalSeconds % 60);

    let result = '';

    if (hours > 0) {
      result += hours + ':';
    }
    result += minutes < 10 ? '0' + minutes : minutes;
    result += ':';
    result += seconds < 10 ? '0' + seconds : seconds;

    return result;
  }
}
