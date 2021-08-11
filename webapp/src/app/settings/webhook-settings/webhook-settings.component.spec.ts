import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WebhookSettingsComponent } from './webhook-settings.component';

describe('WebhookSettingsComponent', () => {
  let component: WebhookSettingsComponent;
  let fixture: ComponentFixture<WebhookSettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WebhookSettingsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WebhookSettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
