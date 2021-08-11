import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'filename',
})
export class FilenamePipe implements PipeTransform {
  transform(path: string): string {
    if (!path) {
      return '';
    }
    if (path.startsWith('/')) {
      return path.split('/').pop() ?? '';
    } else {
      return path.split('\\').pop() ?? '';
    }
  }
}
