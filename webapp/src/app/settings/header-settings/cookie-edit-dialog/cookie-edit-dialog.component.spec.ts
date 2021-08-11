import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CookieEditDialogComponent } from './cookie-edit-dialog.component';

describe('CookieEditDialogComponent', () => {
  let component: CookieEditDialogComponent;
  let fixture: ComponentFixture<CookieEditDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ CookieEditDialogComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(CookieEditDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
