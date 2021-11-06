import { Pipe, PipeTransform } from '@angular/core';

import { Progress } from 'src/app/tasks/shared/task.model';

@Pipe({
  name: 'progress',
})
export class ProgressPipe implements PipeTransform {
  transform(progress: Progress): number {
    if (!progress || progress.duration === 0) {
      return 0;
    }
    return Math.round((progress.time / progress.duration) * 100);
  }
}
