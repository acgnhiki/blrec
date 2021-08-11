import { TestBed } from '@angular/core/testing';

import { SettingsSyncService } from './settings-sync.service';

describe('SettingsSyncService', () => {
  let service: SettingsSyncService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SettingsSyncService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
