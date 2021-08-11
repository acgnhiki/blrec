import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UserAgentEditDialogComponent } from './user-agent-edit-dialog.component';

describe('UserAgentEditDialogComponent', () => {
  let component: UserAgentEditDialogComponent;
  let fixture: ComponentFixture<UserAgentEditDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ UserAgentEditDialogComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(UserAgentEditDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
