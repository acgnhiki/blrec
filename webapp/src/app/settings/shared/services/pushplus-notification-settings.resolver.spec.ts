import { TestBed } from '@angular/core/testing';

import { PushplusNotificationSettingsResolver } from './pushplus-notification-settings.resolver';

describe('PushplusNotificationSettingsResolverService', () => {
  let service: PushplusNotificationSettingsResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PushplusNotificationSettingsResolver);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
