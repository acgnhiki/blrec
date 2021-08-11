import { Pipe, PipeTransform } from '@angular/core';

import { TaskData } from '../task.model';

export function* filter<T>(
  it: Iterable<T>,
  predicate: (value: T) => unknown
): Generator<T> {
  for (const item of it) {
    if (predicate(item)) {
      yield item;
    }
  }
}

@Pipe({
  name: 'filterTasks',
})
export class FilterTasksPipe implements PipeTransform {
  transform(dataList: Iterable<TaskData>, term: string = ''): TaskData[] {
    console.debug("filter tasks by '%s'", term);
    return [...this.filterByTerm(dataList, term)];
  }

  private filterByTerm(dataList: Iterable<TaskData>, term: string) {
    return filter(dataList, (data) => {
      term = term.trim();
      return (
        term === '' ||
        data.user_info.name.includes(term) ||
        data.room_info.title.toString().includes(term) ||
        data.room_info.area_name.toString().includes(term) ||
        data.room_info.room_id.toString().includes(term) ||
        data.room_info.short_room_id.toString().includes(term)
      );
    });
  }
}
