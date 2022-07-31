import { Pipe, PipeTransform } from '@angular/core';
import { formatDuration } from '../utils';

@Pipe({
  name: 'duration',
})
export class DurationPipe implements PipeTransform {
  transform(totalSeconds: number): string {
    return formatDuration(totalSeconds, true);
  }
}
