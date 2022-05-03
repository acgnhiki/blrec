import { TestBed } from '@angular/core/testing';

import { PushdeerNotificationSettingsResolver } from './pushdeer-notification-settings.resolver';

describe('PushdeerNotificationSettingsResolver', () => {
  let service: PushdeerNotificationSettingsResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PushdeerNotificationSettingsResolver);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
