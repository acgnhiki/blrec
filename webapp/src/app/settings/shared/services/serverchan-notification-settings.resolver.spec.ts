import { TestBed } from '@angular/core/testing';

import { ServerchanNotificationSettingsResolver } from './serverchan-notification-settings.resolver';

describe('ServerchanNotificationSettingsResolverService', () => {
  let service: ServerchanNotificationSettingsResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ServerchanNotificationSettingsResolver);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
