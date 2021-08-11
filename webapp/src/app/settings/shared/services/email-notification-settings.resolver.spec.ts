import { TestBed } from '@angular/core/testing';

import { EmailNotificationSettingsResolver } from './email-notification-settings.resolver';

describe('EmailNotificationSettingsResolverService', () => {
  let service: EmailNotificationSettingsResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(EmailNotificationSettingsResolver);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
