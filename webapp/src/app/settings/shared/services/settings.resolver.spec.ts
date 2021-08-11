import { TestBed } from '@angular/core/testing';

import { SettingsResolver } from './settings.resolver';

describe('SettingsResolverService', () => {
  let service: SettingsResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SettingsResolver);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
