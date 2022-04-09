import { TestBed } from '@angular/core/testing';

import { TaskSettingsService } from './task-settings.service';

describe('TaskSettingsService', () => {
  let service: TaskSettingsService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TaskSettingsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
