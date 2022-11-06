import { TestBed } from '@angular/core/testing';

import { BarkNotificationSettingsResolver } from './bark-notification-settings.resolver';

describe('TelegramNotificationSettingsResolverService', () => {
  let service: BarkNotificationSettingsResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(BarkNotificationSettingsResolver);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
