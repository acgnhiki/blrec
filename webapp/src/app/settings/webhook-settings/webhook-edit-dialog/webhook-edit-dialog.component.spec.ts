import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WebhookEditDialogComponent } from './webhook-edit-dialog.component';

describe('WebhookEditDialogComponent', () => {
  let component: WebhookEditDialogComponent;
  let fixture: ComponentFixture<WebhookEditDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WebhookEditDialogComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WebhookEditDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
