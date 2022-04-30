import { TestBed } from '@angular/core/testing';

import { TelegramNotificationSettingsResolver } from './telegram-notification-settings.resolver';

describe('TelegramNotificationSettingsResolverService', () => {
  let service: TelegramNotificationSettingsResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TelegramNotificationSettingsResolver);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
