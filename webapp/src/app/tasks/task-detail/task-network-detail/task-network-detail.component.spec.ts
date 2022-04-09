import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TaskNetworkDetailComponent } from './task-network-detail.component';

describe('TaskNetworkDetailComponent', () => {
  let component: TaskNetworkDetailComponent;
  let fixture: ComponentFixture<TaskNetworkDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TaskNetworkDetailComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TaskNetworkDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
