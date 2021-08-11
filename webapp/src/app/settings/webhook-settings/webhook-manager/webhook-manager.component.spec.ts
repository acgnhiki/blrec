import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WebhookManagerComponent } from './webhook-manager.component';

describe('WebhookManagerComponent', () => {
  let component: WebhookManagerComponent;
  let fixture: ComponentFixture<WebhookManagerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WebhookManagerComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WebhookManagerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
