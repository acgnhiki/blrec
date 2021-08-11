import { TestBed } from '@angular/core/testing';

import { TaskManagerService } from './task-manager.service';

describe('TaskManagerService', () => {
  let service: TaskManagerService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TaskManagerService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
