import { TestBed } from '@angular/core/testing';

import { ExceptionService } from './exception.service';

describe('ExceptionService', () => {
  let service: ExceptionService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ExceptionService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
