import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BaseLiveApiUrlEditDialogComponent } from './base-live-api-url-edit-dialog.component';

describe('BaseLiveApiUrlEditDialogComponent', () => {
  let component: BaseLiveApiUrlEditDialogComponent;
  let fixture: ComponentFixture<BaseLiveApiUrlEditDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ BaseLiveApiUrlEditDialogComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(BaseLiveApiUrlEditDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
